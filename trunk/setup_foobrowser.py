from distutils.core import setup
import py2exe
setup(windows=[
    { "script":"foobrowser.pyw", 
      "icon_resources":[(1, "foobrowser.ico")]
    }
    ])
