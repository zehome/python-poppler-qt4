#! python

project = dict(
    name = 'python-poppler-qt4',
    version = '0.25.0',
    description = 'A Python binding to Poppler-Qt4',
    long_description = (
        'A Python binding to Poppler-Qt4 that aims for '
        'completeness and for being actively maintained. '
        'Using this module you can access the contents of PDF files '
        'inside PyQt4 applications.'
    ),
    maintainer = 'Wilbert Berendsen',
    maintainer_email = 'wbsoft@xs4all.nl',
    url = 'https://github.com/wbsoft/python-poppler-qt4',
    license = 'LGPL',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Graphics :: Viewers',
    ],
    cmdclass={}
)

import os
import re
import shlex
import subprocess
import sys
import platform

try:
   from setuptools import setup, Extension
except ImportError:
   from distutils.core import setup, Extension
   
import sipdistutils

### this circumvents a bug in sip < 4.14.2, where the file() builtin is used
### instead of open()
try:
    import builtins
    try:
        builtins.file
    except AttributeError:
        builtins.file = open
except ImportError:
    pass
### end

def pkg_config(package, attrs=None, include_only=False):
    """parse the output of pkg-config for a package.
    
    returns the given or a new dictionary with one or more of these keys
    'include_dirs', 'library_dirs', 'libraries'. Every key is a list of paths,
    so that it can be used with distutils Extension objects.
    
    """
    if attrs is None:
        attrs = {}
    cmd = ['pkg-config']
    if include_only:
        cmd += ['--cflags-only-I']
    else:
        cmd += ['--cflags', '--libs']
    cmd.append(package)
    try:
        output = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    except OSError:
        return attrs
    flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
    # for python3 turn bytes back to string
    if sys.version_info[0] > 2:
        output = output.decode('utf-8')
    for flag in shlex.split(output):
        option, path = flag[:2], flag[2:]
        if option in flag_map:
            l = attrs.setdefault(flag_map[option], [])
            if path not in l:
                l.append(path)
    return attrs

def pkg_config_version(package):
    """Returns the version of the given package as a tuple of ints."""
    cmd = ['pkg-config', '--modversion', package]
    try:
        output = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
        # for python3 turn bytes back to string
        if sys.version_info[0] > 2:
            output = output.decode('utf-8')
        return tuple(map(int, re.findall(r'\d+', output)))
    except OSError:
        sys.stderr.write("Can't determine version of %s\n" % package)

ext_args = {}
pkg_config('poppler-qt4', ext_args)

if 'libraries' not in ext_args:
    ext_args['libraries'] = ['poppler-qt4']

# hack to provide our options to sip on its invocation:
build_ext_base = sipdistutils.build_ext
class build_ext(build_ext_base):
    
    description = "Builds the popplerqt4 module."
    
    user_options = build_ext_base.user_options + [
        ('poppler-version=', None, "version of the poppler library"),
        ('qmake-bin=', None, "Path to qmake binary"),
        ('qt-include-dir=', None, "Path to Qt headers"),
        ('pyqt-sip-dir=', None, "Path to PyQt's SIP files"),
        ('pyqt-sip-flags=', None, "SIP flags used to generate PyQt bindings")
    ]
    
    def initialize_options (self):
        build_ext_base.initialize_options(self)
        self.poppler_version = None

        self.qmake_bin = 'qmake'

        self.qt_include_dir = None
        self.pyqt_sip_dir = None
        self.pyqt_sip_flags = None

    def finalize_options (self):
        build_ext_base.finalize_options(self)

        if not self.qt_include_dir:
            self.qt_include_dir = self.__find_qt_include_dir()

        if not self.pyqt_sip_dir:
            self.pyqt_sip_dir = self.__find_pyqt_sip_dir()

        if not self.pyqt_sip_flags:
            self.pyqt_sip_flags = self.__find_pyqt_sip_flags()

        if not self.qt_include_dir:
            raise SystemExit('Could not find Qt4 headers. '
                             'Please specify via --qt-include-dir=')

        if not self.pyqt_sip_dir:
            raise SystemExit('Could not find PyQt SIP files. '
                             'Please specify containing directory via '
                             '--pyqt-sip-dir=')

        if not self.pyqt_sip_flags:
            raise SystemExit('Could not find PyQt SIP flags. '
                             'Please specify via --pyqt-sip-flags=')

        self.include_dirs += (self.qt_include_dir,
                              os.path.join(self.qt_include_dir, 'QtCore'),
                              os.path.join(self.qt_include_dir, 'QtGui'),
                              os.path.join(self.qt_include_dir, 'QtXml'))

        if self.poppler_version is not None:
            self.poppler_version = tuple(map(int, re.findall(r'\d+', self.poppler_version)))

    def __find_qt_include_dir(self):
        if self.pyqtconfig:
            return self.pyqtconfig.qt_inc_dir

        try:
            qt_version = subprocess.check_output([self.qmake_bin,
                                                  '-query',
                                                  'QT_VERSION'])
            qt_version = qt_version.strip().decode("ascii")
        except (OSError, subprocess.CalledProcessError) as e:
            raise SystemExit('Failed to determine Qt version (%s).' % e)

        if not qt_version.startswith("4."):
            raise SystemExit('Unsupported Qt version (%s). '
                             'Try specifying the path to qmake manually via '
                             '--qmake-bin=' % qt_version)

        try:
            result =  subprocess.check_output([self.qmake_bin,
                                               '-query',
                                               'QT_INSTALL_HEADERS'])
            return result.strip().decode(sys.getfilesystemencoding())
        except (OSError, subprocess.CalledProcessError) as e:
            raise SystemExit('Failed to determine location of Qt headers (%s).' % e)

    def __find_pyqt_sip_dir(self):
        if self.pyqtconfig:
            return self.pyqtconfig.pyqt_sip_dir

        import sipconfig

        return os.path.join(sipconfig.Configuration().default_sip_dir, 'PyQt4')

    def __find_pyqt_sip_flags(self):
        if self.pyqtconfig:
            return self.pyqtconfig.pyqt_sip_flags

        from PyQt4 import QtCore

        return QtCore.PYQT_CONFIGURATION.get('sip_flags', '')

    @property
    def pyqtconfig(self):
        if not hasattr(self, '_pyqtconfig'):
            try:
                from PyQt4 import pyqtconfig

                self._pyqtconfig = pyqtconfig.Configuration()
            except ImportError:
                self._pyqtconfig = None

        return self._pyqtconfig

    def write_version_sip(self, poppler_qt4_version, python_poppler_qt4_version):
        """Write a version.sip file.
        
        The file contains code to make version information accessible from
        the popplerqt4 Python module.
        
        """
        with open('version.sip', 'w') as f:
            f.write(version_sip_template.format(
                vlen = 'i' * len(python_poppler_qt4_version),
                vargs = ', '.join(map(format, python_poppler_qt4_version)),
                pvlen = 'i' * len(poppler_qt4_version),
                pvargs = ', '.join(map(format, poppler_qt4_version))))
        
    def _sip_compile(self, sip_bin, source, sbf):
        
        # First check manually specified poppler version
        ver = self.poppler_version or pkg_config_version('poppler-qt4') or ()
        
        # our own version:
        version = tuple(map(int, re.findall(r'\d+', project['version'])))
        
        # make those accessible from the popplerqt4 module:
        self.write_version_sip(ver, version)
        
        # Disable features if older poppler-qt4 version is found.
        # See the defined tags in %Timeline{} in poppler-qt4.sip.
        if not ver or ver < (0, 12, 1):
            tag = 'POPPLER_V0_12_0'
        elif ver < (0, 14, 0):
            tag = 'POPPLER_V0_12_1'
        elif ver < (0, 16, 0):
            tag = 'POPPLER_V0_14_0'
        elif ver < (0, 18, 0):
            tag = 'POPPLER_V0_16_0'
        elif ver < (0, 20, 0):
            tag = 'POPPLER_V0_18_0'
        elif ver < (0, 22, 0):
            tag = 'POPPLER_V0_20_0'
        elif ver < (0, 24, 0):
            tag = 'POPPLER_V0_22_0'
        else:
            tag = 'POPPLER_V0_24_0'
        
        cmd = [sip_bin]
        if hasattr(self, 'sip_opts'):
            cmd += self.sip_opts
        if hasattr(self, '_sip_sipfiles_dir'):
            cmd += ['-I', self._sip_sipfiles_dir()]
        if tag:
            cmd += ['-t', tag]
        cmd += [
            "-c", self.build_temp,
            "-b", sbf,
            "-I", self.pyqt_sip_dir]             # find the PyQt4 stuff
        cmd += shlex.split(self.pyqt_sip_flags)  # use same SIP flags as for PyQt4
        cmd.append(source)
        self.spawn(cmd)

if platform.system() == 'Windows':
   # Enforce libraries to link against on Windows
   ext_args['libraries'] = ['poppler-qt4', 'QtCore4', 'QtGui4', 'QtXml4']
   
   class bdist_support():
       def __find_poppler_dll(self):
           paths = os.environ['PATH'].split(";")
           poppler_dll = None
           
           for path in paths:
               dll_path_candidate = os.path.join(path, "poppler-qt4.dll")
               if os.path.exists(dll_path_candidate):
                   return dll_path_candidate
           
           return None
       
       def _copy_poppler_dll(self):
           poppler_dll = self.__find_poppler_dll()
           if poppler_dll is None:
               self.warn("Could not find poppler-qt4.dll in any of the folders listed in the PATH environment variable.")
               return False
               
           self.mkpath(self.bdist_dir)
           self.copy_file(poppler_dll, os.path.join(self.bdist_dir, "python-poppler4.dll"))
           
           return True
   
   import distutils.command.bdist_msi
   class bdist_msi(distutils.command.bdist_msi.bdist_msi, bdist_support):
       def run(self):
           if not self._copy_poppler_dll():
               return
           distutils.command.bdist_msi.bdist_msi.run(self)
   
   project['cmdclass']['bdist_msi'] = bdist_msi
   
   import distutils.command.bdist_wininst
   class bdist_wininst(distutils.command.bdist_wininst.bdist_wininst, bdist_support):
       def run(self):
           if not self._copy_poppler_dll():
               return
           distutils.command.bdist_wininst.bdist_wininst.run(self)
   project['cmdclass']['bdist_wininst'] = bdist_wininst
   
   import distutils.command.bdist_dumb
   class bdist_dumb(distutils.command.bdist_dumb.bdist_dumb, bdist_support):
       def run(self):
           if not self._copy_poppler_dll():
               return
           distutils.command.bdist_dumb.bdist_dumb.run(self)
   project['cmdclass']['bdist_dumb'] = bdist_dumb
   
   try:
       # Attempt to patch bdist_egg if the setuptools/distribute extension is installed
       import setuptools.command.bdist_egg
       class bdist_egg(setuptools.command.bdist_egg.bdist_egg, bdist_support):
           def run(self):
               if not self._copy_poppler_dll():
                   return
               setuptools.command.bdist_egg.bdist_egg.run(self)
       project['cmdclass']['bdist_egg'] = bdist_egg
   except ImportError:
       pass


version_sip_template = r"""// Generated by setup.py -- Do not edit

PyObject *version();
%Docstring
The version of the popplerqt4 python module.
%End

PyObject *poppler_version();
%Docstring
The version of the Poppler library.
%End

%ModuleCode

PyObject *version()
{{ return Py_BuildValue("({vlen})", {vargs}); }};

PyObject *poppler_version()
{{ return Py_BuildValue("({pvlen})", {pvargs}); }};

%End
"""

### use full README.rst as long description
with open('README.rst', 'rb') as f:
    project["long_description"] = f.read().decode('utf-8')


   
project['cmdclass']['build_ext'] = build_ext
setup(
    ext_modules = [Extension("popplerqt4", ["poppler-qt4.sip"], **ext_args)],
    **project
)
