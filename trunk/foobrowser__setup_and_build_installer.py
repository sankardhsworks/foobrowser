# script to perform the py2exe setup and then get innosetup to build the installer
# optionally can increment the version number of the output setup

from distutils.core import setup
import py2exe
import os
import sys
import subprocess

def copy_plugins(pluginsdir, distdir, plugintype):
  dst = os.path.join(distdir, plugintype)
  print("copy_plugins: dst: %s" % (dst))
  if not os.path.isdir(dst):
    try:
      os.mkdir(dst)
    except Exception as e:
      print("Unable to make plugins destination dir %s, bailing out" % (dst))
      print("(%s)" % (str(e)))
      sys.exit(2)
  src = os.path.join(pluginsdir, plugintype)
  if not os.path.isdir(src):
    print("Unable to find source plugins at %s, bailing out" % (src))
    sys.exit(3)
  for f in os.listdir(src):
    sys.stdout.write(" copy plugin %s :: %s" % (plugintype, f))
    sys.stdout.flush()
    try:
      open(os.path.join(dst, f), "wb").write(open(os.path.join(src, f), "rb").read())
      print("(ok)")
    except Exception as e:
      print("(fail)")
      print("(%s)" % (str(e)))
      sys.exit(4)

if __name__ == "__main__":
  print(">>> Generating distributable contents")
  cmd = "%s %s %s" % (sys.executable, os.path.join(os.path.dirname(sys.argv[0]), "setup_foobrowser.py"), "py2exe")
  os.system(cmd)
  print(">>> Ensuring Qt plugins are in place")
  pydir = os.path.dirname(sys.executable)
  pluginsdir = os.path.join(pydir, "Lib", "site-packages", "PyQt4", "plugins")
  if not os.path.isdir(pluginsdir):
    print("Unable to find Qt plugins at %s, bailing out" % (pluginsdir))
    sys.exit(1)
  for ptype in ["codecs", "imageformats"]:
    copy_plugins(pluginsdir, os.path.join(os.path.dirname(sys.argv[0]), "dist"), ptype)

  iss_file = os.path.join(os.path.dirname(sys.argv[0]), "foobrowser.iss")
  if "-incver" in sys.argv[1:]:
    new_iss = []
    for line in open(iss_file, "r"):
      line = line.strip()
      parts = line.split(" ")
      if len(parts) == 3 and parts[0] == "#define" and parts[1] == "MyAppVersion":
        ver = float(parts[2].strip("\""))
        ver += 0.1
        parts[2] = "\"%.1f\"" % (ver)
        line = " ".join(parts)
      new_iss.append(line)
    open(iss_file, "w").write("\n".join(new_iss))
  cmd = "\"C:\\Program Files (x86)\\Inno Setup 5\\Compil32.exe\" /cc \"%s\"" % (iss_file)
  print(">>> building setup")
  print(cmd)
  subprocess.call(cmd)
