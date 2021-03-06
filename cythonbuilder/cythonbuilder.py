import os
from dataclasses import dataclass
# from __future__ import print_function, division
import sys
import os
import logging
import shutil
from glob import glob
# from . import config
from .config import AppConfig, LoggingConfig, DirConfig

logging.basicConfig(
    level=logging.CRITICAL,
    # format=f'[{appname}] - %(levelname)s [%(asctime)s] %(message)s',
    format=f'[{AppConfig.appname}] %(asctime)s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(LoggingConfig.loggingName)
logger.setLevel(logging.INFO)


def init():
    """ Creates a folder-structure for all pyx-files and resulting so-files like
    - root
        - ext (holds all so-files)
            - pyxfiles
            - annotations
   """



    required_folders = [
        DirConfig.root,
        DirConfig.ext,
        DirConfig.pyx,
        DirConfig.anno
    ]


    # Ensure folder structure exists
    for folder in required_folders:
        if (not os.path.isdir(folder)):
            os.mkdir(folder)
            logger.debug(f"created {folder}")

    # Warn if folder contain files
    for _dir in [DirConfig.ext, DirConfig.pyx]:
        file_list = next(os.walk(_dir), (None, None, []))[2]  # [] if no file
        if (len(file_list) > 0):
            logger.debug(f"{_dir} folder is not empty")

    logger.info("Initialized")

def help():
    print(f"""{AppConfig.appname}
        Automatically builds and packages your Cython code 
        1. Initialize {AppConfig.appname} with `{AppConfig.appcmd} init` 
        2. Place all .pyx Cython files in {DirConfig.dirname_extensions}/{DirConfig.dirname_pyxfiles}
        3. Call `{AppConfig.appcmd} build` to build and package all .pyx files in {DirConfig.dirname_extensions}/{DirConfig.dirname_pyxfiles} 
            Alternatively call `{AppConfig.appcmd} build filename1, filename2` (without .pyx extension) to build specific files
        4. Import your compile package from {DirConfig.dirname_extensions}/ like `from {DirConfig.dirname_extensions} import filename`
    
        Commands:
        (call either command with --debug to get more information)
        init        Initialized the folders
        help        Show this screen
        build       Build and package cython files
          --no-numpy-required Prevents numpy being included in setup.py include_dirs (default True)
          --no-annotation     Disables generating the annotations html (default True)
          --keep-c-files      Prevents removal of intermediate C files that Cython generates (default True)
        clean       Cleans up project. Puts all built files in {DirConfig.dirname_extensions}, removes 
          --no-annotation     Disables generating the annotations html (default True)
          --keep-c-files      Prevents removal of intermediate C files that Cython generates (default True)
        """)

def build(include_annotation:bool=True, numpy_required:bool=True, targetfilenames:[str]=None, debugmode:bool=False, keep_c_files:bool=False):
    """ Builds and cleans """
    just_build(include_annotation=include_annotation, numpy_required=numpy_required, targetfilenames=targetfilenames, debugmode=debugmode)
    clean(keep_c_files=keep_c_files, keep_annotation_files=include_annotation)

def just_build(include_annotation:bool=True, numpy_required:bool=True, targetfilenames:[str]=None, debugmode:bool=False):
    """ pyx -> c -> pyd """


    if (debugmode):
        logger.setLevel(logging.DEBUG)

    # Parse arguments
    if (targetfilenames == None):
        targetfilenames = []


    # Find paths for all target files; optionally filter on user input
    target_pyx_filepaths = [y for x in os.walk(DirConfig.ext) for y in glob(os.path.join(x[0], '*.pyx'))]
    target_pyx_filenames = [os.path.basename(p) for p in target_pyx_filepaths]
    logger.debug(f"Filenames in folder: {target_pyx_filenames}")


    # If user passes targetfilenames
    if (len(targetfilenames) > 0):
        logger.debug(f'Target filenames: {targetfilenames})')

        # Check if all provided file names exist
        missing_pyx_filepaths = [p for p in targetfilenames if f"{p}.pyx" not in target_pyx_filenames]
        if (len(missing_pyx_filepaths) > 0):
            logger.error('Could not find these files:')
            for f in missing_pyx_filepaths:
                logger.error(f'\t{f}')
            logger.error('Aborting.')
            sys.exit(2)

        # Filter our target files with the provided file names
        target_pyx_filepaths = [p for p in target_pyx_filepaths for f in targetfilenames if f"{f}.pyx" in p]
        target_pyx_filenames = [os.path.basename(p) for p in target_pyx_filepaths]
        logger.debug(msg=f"Found all target filepaths: {target_pyx_filepaths}")


    # NO pyx files found
    if (len(target_pyx_filepaths) == 0):
        logger.error('No pyx files found to compile')
        sys.exit(1)



    # START SETUP
    logger.debug(msg=f"Start setup")
    sys.argv = [sys.argv[0], 'build_ext', '--inplace']
    from setuptools import setup, Extension
    from Cython.Distutils import build_ext
    from Cython.Build import cythonize
    import Cython.Compiler.Options


    # Set compiler options
    Cython.Compiler.Options.annotate = include_annotation

    # Create module objects
    logger.debug(msg=f"Creating module objects")
    ext_modules = []
    for n in target_pyx_filepaths:
        module_name, extension = os.path.splitext(os.path.basename(n))
        # The name must be plain, no path
        obj = Extension(
            name=module_name,
            sources=[n],
            # extra_compile_args=["-O2", "-march=native"]
        )
        ext_modules.append(obj)
    logger.debug(msg=f"Included {len(ext_modules)} modules")

    # Extra include folders. Mainly for numpy.
    logger.debug(msg=f"Including directories")
    include_dirs = []
    if (numpy_required):
        try:
            import numpy
            include_dirs += [numpy.get_include()]
        except Exception as e:
            logger.debug(msg=f"{type(e).__name__}: {e}")
            logger.error('Exiting: numpy is required but not found. '
                          '\nFix this issue by either:'
                          '\n - pip install numpy '
                          '\n - indicate that numpy is not required using the --no-numpy-required flag (check out cythonbuilder help for more info)')
            sys.exit(1)
    logger.debug(msg=f"Included {len(include_dirs)} dirs: {include_dirs}")


    logger.debug(msg=f"Starting setup")
    setup(
        cmdclass={'build_ext': build_ext},
        include_dirs=include_dirs,
        ext_modules = cythonize(ext_modules, quiet=True),
        # buid_dir=path_build_dir
    )

    logger.debug(msg=f"Built and packaged {len(ext_modules)} module(s): {[os.path.splitext(fn)[0] for fn in target_pyx_filenames]}")
    logger.info(msg=f"Built and packaged {len(ext_modules)} module(s): {', '.join([os.path.splitext(fn)[0] for fn in target_pyx_filenames])}")
def clean(keep_c_files:bool=False, keep_annotation_files:bool=True, debugmode:bool=False):
    """
    Removes c
    """

    if (debugmode):
        logger.setLevel(logging.DEBUG)

    logger.debug(msg=f"Starting cleanup")

    all_c_files = [y for x in os.walk(DirConfig.pyx) for y in glob(os.path.join(x[0], '*.c'))]
    all_html_files = [y for x in os.walk(DirConfig.pyx) for y in glob(os.path.join(x[0], '*.html'))]
    all_built_files = [p for p in os.listdir(DirConfig.root) if ('.pyd' in p or '.so' in p)]


    # 1. delete intermediate C files.
    if (not keep_c_files):
        for cpath in all_c_files:
            if os.path.exists(cpath):
                os.remove(cpath)
            else:
                logger.warning(msg=f"Moving C file; {cpath} doesn't exist")
        logger.debug(msg=f"Removed {len(all_c_files)} C files from {DirConfig.dirname_pyxfiles} folder")

    # 2. Move all annotations
    if (keep_annotation_files):
        for htmlpath in all_html_files:
            shutil.move(htmlpath, os.path.join(DirConfig.anno, os.path.basename(htmlpath)))
        logger.debug(msg=f"Moved {len(all_html_files)} annotation files to {DirConfig.dirname_extensions}/{DirConfig.dirname_pyxfiles}")
    else:
        for htmlpath in all_html_files:
            if (os.path.exists(htmlpath)):
                os.remove(htmlpath)

    # 3. Move all built (.pyd / .so) files from the root o in the project to the extensions dir
    for bfile in all_built_files:
        shutil.move(
            src=os.path.join(DirConfig.root, bfile),
            dst=os.path.join(DirConfig.ext, bfile)
        )
    logger.debug(msg=f"Moved {len(all_built_files)} built files (.pyd / .so) to {DirConfig.dirname_extensions}/")

    # 4. Remove setup.py build dir that contains compiled c
    try:
        shutil.rmtree(DirConfig.build)
    except Exception as e:
        logger.debug("Cleanup: build folder cannot be located")
    logger.debug(msg=f"Clean up process completed")
    logger.info(msg=f"Clean-up process completed")

def test(_args):
    logger.setLevel(logging.DEBUG)
    logger.debug(msg=f"args: {_args}")


def main():
    _args = sys.argv[1:]

    # No commands
    if (len(_args) == 0):
        help()
        sys.exit(1)

    # Set debugger
    if ('--debug' in _args):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


    # Parse commands
    command = _args.pop(0)
    if (command == 'init'):
        init()
    elif (command in  ['--help', 'h', 'help']):
        help()
    elif (command == 'build'):
        # Parse args
        include_annotation = False if ('--no-annotation' in _args) else True    # default True
        numpy_required = False if ('--no-numpy-required' in _args) else True    # default True
        keep_c_files = True if ('--keep-c-files' in _args) else False           # default False
        keep_annotations = False if ('--no-annotations' in _args) else True         # default False

        # Clean up _args
        targetfilenames = [a for a in _args if a[:2] != '--']

        # Call build function
        try:
            just_build(
                include_annotation=include_annotation,
                numpy_required=numpy_required,
                targetfilenames=targetfilenames
            )
        except Exception as e:
            logger.error(f"An error occurred executing the build command: \n{e}")
        finally:
            clean(
                keep_c_files=keep_c_files,
                keep_annotation_files=keep_annotations
            )
    elif (command == 'clean'):
        keep_c_files = True if ('--keep-c-files' in _args) else False           # default False
        keep_annotations = False if ('--no-annotations' in _args) else True         # default False
        clean(keep_c_files=keep_c_files, keep_annotation_files=keep_annotations)
    elif (command == 'test'):
        test(_args)
    else:
        help()

if (__name__ == "__main__"):
    main()