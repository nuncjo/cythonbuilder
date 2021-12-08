from __future__ import print_function, division
import sys
import os
import logging
import shutil
import typing
from os.path import splitext
from pathlib import Path
from glob import glob


dirname_extensions = "ext"
dirname_pyxfiles = "pyxfiles"
dirname_annotations = "annotations"

path_root_dir = os.path.realpath(os.curdir)
path_extensions_dir = os.path.join(path_root_dir, dirname_extensions)
path_pyx_dir = os.path.join(path_extensions_dir, dirname_pyxfiles)
path_annotations_dir = os.path.join(path_extensions_dir, dirname_annotations)
path_setuppy_build_dir = os.path.join(path_root_dir, 'build')

appname = "CythonBuilder"
appcmd = os.path.splitext(os.path.basename(__file__))[0]


logging.basicConfig(
    level=logging.NOTSET,
    format=f'[{appname}] - %(levelname)s [%(asctime)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)


def init():
    """ Creates a folder-structure for all pyx-files and resulting so-files like
    - root
        - ext (holds all so-files)
            - cythonfiles
   """


    required_folders = [path_root_dir, path_extensions_dir, path_pyx_dir, path_annotations_dir]


    # Ensure folder structure exists
    for folder in required_folders:
        if (not os.path.isdir(folder)):
            os.mkdir(folder)

    # Warn if folder contain files
    for _dir in [path_extensions_dir, path_pyx_dir]:
        file_list = next(os.walk(_dir), (None, None, []))[2]  # [] if no file
        if (len(file_list) > 0):
            logging.warning(f"{_dir} folder is not empty")

    logging.info("Initialized")

def help():
    print(f"""{appname}
    Automatically builds and packages your Cython code 
    1. Initialize {appname} with `{appcmd} init` 
    2. Place all .pyx Cython files in {dirname_extensions}/{dirname_pyxfiles}
    3. Call `{appcmd} build` to build and package all .pyx files in {dirname_extensions}/{dirname_pyxfiles} 
        Alternatively call `{appcmd} build filename1, filename2` (without .pyx extension) to build specific files
    4. Import your compile package from {dirname_extensions}/ like `from {dirname_extensions} import filename`

    init        Initialized the folders
    help        Show this screen
    build       Build and package cython files
      --debug             Debugging mode (default False)
      --no-annotation     Disables generating the annotations html (default True)
      --no-numpy-required Prevents numpy being included in setup.py include_dirs (default True)
      --keep-c-files      Prevents removal of intermediate C files that Cython generates (default True)
    """)

def build(include_annotation:bool=True, numpy_required:bool=False, debugmode:bool=False, keep_c_files:bool=False, targetfilenames:[str]=None):
    """ pyx -> c -> so
    annotation: whether or not to generate the annotation html
    """

    # SET LOGGER
    if (debugmode):
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


    # Parse arguments
    if (targetfilenames == None):
        targetfilenames = []


    # Find paths for all target files; optionally filter on user input
    target_pyx_filepaths = [y for x in os.walk(path_extensions_dir) for y in glob(os.path.join(x[0], '*.pyx'))]
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
        logger.debug(msg=f"Found all target filepaths: {target_pyx_filepaths}")

    # NO pyx files found
    if (len(target_pyx_filepaths) == 0):
        logging.error('No pyx files found to compile')
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
            logging.error('Exiting: numpy is required but not found. Please pip install numpy')
            sys.exit(1)
    logger.debug(msg=f"Included {len(include_dirs)} dirs: {include_dirs}")


    logging.debug(msg=f"Starting setup")
    setup(
        cmdclass={'build_ext': build_ext},
        include_dirs=include_dirs,
        ext_modules = cythonize(ext_modules),
        # buid_dir=path_build_dir
    )
    logger.debug(msg=f"Built {len(target_pyx_filenames)} modules: {[os.path.splitext(fn)[0] for fn in target_pyx_filenames]}")



    # CLEANUP
    logger.debug(msg=f"Starting cleanup")

    # 1. delete intermediate C files.
    if (not keep_c_files):
        logger.debug(msg=f"Removing C files")
        for pyxpath in target_pyx_filepaths:
            cpath = pyxpath.replace(".pyx", ".c")
            if os.path.exists(cpath):
                os.remove(cpath)
            else:
                logger.warning(msg=f"Moving C file; {cpath} doesn't exist")
        logger.debug("Removed C files")

    # 2. Move all annotations
    for pyxpath in target_pyx_filepaths:
        htmlpath = pyxpath.replace(".pyx", ".html")
        shutil.move(htmlpath, os.path.join(path_annotations_dir, os.path.basename(htmlpath)))
    logger.debug(msg=f"Moved annotation files to {dirname_extensions}/{dirname_pyxfiles}")

    # 3. Move all pyd files to the extensions dir
    for file in [f for f in os.listdir(path_root_dir) if '.pyd' in f]:
        shutil.move(
            src=os.path.join(path_root_dir, file),
            dst=os.path.join(path_extensions_dir, file)
        )
    logger.debug(msg=f"Moved pyd file to {dirname_extensions}/")

    # 4. Remove setup.py build dir that contains compiled c
    shutil.rmtree(path_setuppy_build_dir)
    logger.debug(msg=f"Removed build dir")
    logger.info(msg=f"Built {len(target_pyx_filenames)} modules: {', '.join([os.path.splitext(fn)[0] for fn in target_pyx_filenames])}")


def test(_args):
    logger.setLevel(logging.DEBUG)
    logger.debug(msg=f"args: {_args}")


def main():
    _args = sys.argv[1:]

    if (len(_args) == 0):
        help()
        sys.exit(1)

    if ('--debug' in _args):
        logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.debug(_args)

    if (_args[0] == 'init'):
        init()
    elif (_args[0] in ('--help', 'h', 'help')):
        help()
    elif (_args[0] in ('build')):
        # Parse args
        include_annotation = False if ('--no-annotation' in _args) else True    # default True
        do_debug = True if ('--debug' in _args) else False                      # default False
        numpy_required = False if ('--no-numpy-required' in _args) else True    # default True
        keep_c_files = True if ('--keep-c-files' in _args) else False           # default False

        # Clean up _args
        targetfilenames = [a for a in _args if a not in ['build', '--no-annotation', '--debug', '--no-numpy-required', '--keep-c-files']]

        # Call build function
        build(
            include_annotation=include_annotation,
            debugmode=do_debug,
            numpy_required=numpy_required,
            keep_c_files=keep_c_files,
            targetfilenames=targetfilenames
        )
    elif (_args[0]) in ('test'):
        test(_args)
    else:
        help()

if (__name__ == "__main__"):
    main()