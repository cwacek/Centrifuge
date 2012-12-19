from setuptools import setup, find_packages

setup(name='centrifuge',
      version='0.1',
      description='Simple service agnostic rotational backup',
      author='Chris Wacek',
      author_email='cwacek@gmail.com',
      url='http://github.com/cwacek/Centrifuge',
      packages=find_packages(),

      entry_points= {
        'console_scripts':
          ["centrifuge = centrifuge.centrifuge:run"]
        }
     )
