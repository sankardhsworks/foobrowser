#!/usr/bin/python
# minimalistic browser levering off of Python, PyQt and Webkit
from PyQt4 import QtGui, QtCore, QtWebKit, QtNetwork
import sqlite3
import os
import sys
import time
import base64
import socket
import sip # put here to make py2exe work better
import subprocess

def registerShortcuts(actions, defaultOwner):
  for action in actions:
    shortcut = actions[action][1]
    if shortcut.lower() == "none":
      continue
# allow multiple shortcuts with keys delimited by |
    shortcuts = shortcut.split("|")
    for shortcut in shortcuts:
      shortcut = shortcut.strip()
      if shortcut == "":
        continue
      callback = actions[action][0]
      if len(actions[action]) == 2:
        owner = defaultOwner
      else:
        if type(actions[action][2]) != str:
          owner = actions[action][2]
        elif len(actions[action]) == 4:
          owner = actions[action][3]
        else:
          owner = defaultOwner
      QtGui.QShortcut(shortcut, owner, callback)

class Icons:
 """Container class to hold icons for Bonsai in base64-encoded format"""
 def __init__(self):
  if os.name == "nt":
   import ctypes
   try:
     ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(os.path.basename(sys.argv[0]))
   except:
# not a win7 client
     pass
  self.icons = dict()
  self.icons["foobrowser"] = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A\
     /wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9sIFw0xIyVxhzgAAAAZdEVYdENv\
     bW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAABJUlEQVR42u3WMUoDURSF4V8JKAoqQlyJ2Fll\
     B+JKRF2ChcsSQU0hSlAXYJoEUihok0KbOxBkeMZ40Vf8HzyGyTtnArd4MyBJkiRJkiRJkiTN4+Ob\
     NasLnAED4C3WIH7rFv5j0V5VA9gDxoXcODJfLdr78wGUbALDyF0BPWA9Vg+4ib1hZH/bq24AJ5G5\
     BVZa9leB+8gcJ/SqG8BlZA4KmcPIXCT0qjkDGpO4Lx1YO5GZJPSqG8A07juF53QiM03o/chy0iCW\
     WlbjNa5bhf52XF8Sev8ygJKnuO4XMs3eQ0KvukPwdI7T/C4yRwm9qr8DruMdvharB/Rj7xnYSOhV\
     NwCAXWBUODBHkcnqVTeAtm/6d+AROI/XWXZPkiRJkiRJkiRJsz4BmPGrGG5RdTEAAAAASUVORK5C\
     YII="
 def QIcon(self, name):
  if list(self.icons.keys()).count(name) == 0:
   return None
  pixmap = QtGui.QPixmap()
  if dir(base64).count("decodebytes"):
    if not pixmap.loadFromData(base64.decodebytes(bytes(self.icons[name], encoding="UTF-8"))):
      return None
  elif dir(base64).count("b64decode"):
    if not pixmap.loadFromData(base64.b64decode(self.icons[name])):
      return None
  icon = QtGui.QIcon(pixmap)
  return icon

class DiskCookies(QtNetwork.QNetworkCookieJar):
  def __init__(self, storage_location, parent=None):
    self.db = None
    QtNetwork.QNetworkCookieJar.__init__(self, parent)
    self.LoadFromDisk(storage_location)

  def LoadFromDisk(self, path):
    cookiefile = os.path.join(path, "cookies.db")
    init = False
    if not os.path.isfile(cookiefile):
      init = True
    self.db = sqlite3.connect(cookiefile)
    if init:
      self.initDB()
    cur = self.db.execute("select domain, expires, http_only, secure, name, path, value from cookies;")
    cookies = []
    for row in cur.fetchall():
      cookie = QtNetwork.QNetworkCookie()
      cookie.setDomain(row[0])
      try:
        if len(row[1]):
          e = time.strptime(row[1], "%Y-%m-%d %H:%M:%S")
          cookie.setExpirationDate(QtCore.QDateTime(e.tm_year, e.tm_mon, e.tm_mday, e.tm_hour, e.tm_min, e.tm_sec))
      except:
        pass
      if row[2]:
        cookie.setHttpOnly(True)
      else:
        cookie.setHttpOnly(False)
      if row[3]:
        cookie.setSecure(True)
      else:
        cookie.setSecure(False)
      cookie.setName(row[4])
      cookie.setPath(row[5])
      try:
        cookie.setValue(bytes(row[6]))
      except:
        try:
          cookie.setValue(bytes(row[6], encoding="UTF-8"))
        except:
          pass
      cookies.append(cookie)
    self.setAllCookies(cookies)

  def clear(self):
    self.setAllCookies([])
    if self.db:
      self.db.execute("delete from cookies;")

  def quote(self, s):
    s = str(s)
    return "'%s'" % (s.replace("'", "''"))

  def boolToInt(self, b):
    if b:
      return 1
    else:
      return 0

  def Persist(self):
    if self.db == None:
      return
    self.db.execute("delete from cookies;")
    sqlstr = "insert into cookies (domain, expires, http_only, secure, name, path, value) values (%s, %s, %i, %i, %s, %s, %s);";
    fmt = "yyyy-MM-dd hh:mm:ss"
    for cookie in self.allCookies():
      cval = cookie.value().data()
      if type(cval) != str:
        cval = cval.decode("UTF-8")
      #print("cookie:\n\tsession: %s\n\tname: %s\n\tpath: %s\n\tvalue: %s\n\t" % (str(cookie.isSessionCookie()),cookie.name(), cookie.path(), cval))
      esql = (sqlstr % (self.quote(cookie.domain()), 
                                self.quote(cookie.expirationDate().toString(fmt)), 
                                self.boolToInt(cookie.isHttpOnly()), 
                                self.boolToInt(cookie.isSecure()), 
                                self.quote(cookie.name()), 
                                self.quote(cookie.path()), 
                                self.quote(cookie.value().data().decode("UTF-8"))))
      self.db.execute(esql)
    self.db.commit()
    self.db.close()

  def initDB(self):
    cur = self.db.execute("create table cookies(domain text, expires text, http_only int, secure int, session int, name text, path text, value text);")
    cur.close()

class FooWebView(QtWebKit.QWebView):
  def __init__(self, parent = None):
    self.parent = parent
    QtWebKit.QWebView.__init__(self, parent)
  def createWindow(self, type):
    return self.parent.browser.addTab().webkit

class WebTab(QtGui.QWidget):
  def __init__(self, browser, actions=None, parent=None, showStatusBar=False):
    QtGui.QWidget.__init__(self, parent)
    self.actions = dict()
    self.grid = QtGui.QGridLayout(self)
    self.grid.setSpacing(1)
    self.cmb = QtGui.QComboBox()
    self.cmb.setEditable(True)
    self.browser = browser
    if browser is not None:
      browser.LoadHistoryToCmb(self.cmb)
    self.webkit = FooWebView(self)
    self.webkit.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
    self.webkit.linkClicked.connect(self.onLinkClick)
    self.webkit.settings().setAttribute(QtWebKit.QWebSettings.PluginsEnabled,True)
    self.pbar = QtGui.QProgressBar()
    self.pbar.setRange(0, 100)
    self.pbar.setTextVisible(False)
    self.grid.addWidget(self.cmb, 0, 0)
    self.grid.addWidget(self.pbar, 1, 0, 1, self.grid.columnCount())
    self.grid.addWidget(self.webkit, 2, 0, 1, self.grid.columnCount())
    self.pbar.setVisible(False)
    self.pbar.setMaximumHeight(10)

    self.fraSearch = QtGui.QFrame()
    self.searchGrid = QtGui.QGridLayout(self.fraSearch)
    self.searchGrid.setSpacing(1)
    self.lblSearch = QtGui.QLabel("Find text in page:")
    self.txtSearch = QtGui.QLineEdit()
    self.btnClearSearch = QtGui.QPushButton("[X]")
    self.searchGrid.addWidget(self.lblSearch, 0, 0)
    self.searchGrid.addWidget(self.txtSearch, 0, 1)
    self.searchGrid.addWidget(self.btnClearSearch, 0, 2)

    self.statusbar = QtGui.QStatusBar()
    self.statusbar.setVisible(showStatusBar)
    self.statusbar.setMaximumHeight(25)
    self.grid.addWidget(self.statusbar, self.grid.rowCount(), 0, 1, self.grid.columnCount())

    for i in range(2):
      self.searchGrid.setColumnStretch(i, i % 2)
    self.fraSearch.setVisible(False)
    self.grid.addWidget(self.fraSearch, self.grid.rowCount() + 1, 0, 1, self.grid.columnCount())

    for c in range(self.grid.columnCount() + 1):
      self.grid.setColumnStretch(c, 0)
    for r in range(self.grid.rowCount() + 1):
      self.grid.setRowStretch(r, 0)
    self.grid.setRowStretch(2, 1)
    self.grid.setColumnStretch(0, 1)

    self.connect(self.cmb, QtCore.SIGNAL("currentIndexChanged(int)"), self.navigate)
    if browser:
      self.browser.setupWebkit(self.webkit)

    self.connect(self.webkit, QtCore.SIGNAL("iconChanged()"), self.setIcon)
    self.connect(self.webkit, QtCore.SIGNAL("loadStarted()"), self.loadStarted)
    self.connect(self.webkit, QtCore.SIGNAL("loadFinished(bool)"), self.loadFinished)
    self.connect(self.webkit, QtCore.SIGNAL("titleChanged(QString)"), self.setTitle)
    self.connect(self.webkit, QtCore.SIGNAL("loadProgress(int)"), self.loadProgress)
    self.connect(self.webkit, QtCore.SIGNAL("urlChanged(QUrl)"), self.setURL)
    self.connect(self.webkit.page(), QtCore.SIGNAL("linkHovered(QString, QString, QString)"), self.onLinkHovered)
    page = self.webkit.page()
    page.downloadRequested.connect(self.onDownloadRequested)
    page.setForwardUnsupportedContent(True)
    page.unsupportedContent.connect(self.onUnsupportedContent)
    self.connect(self.btnClearSearch, QtCore.SIGNAL("clicked()"), self.stopOrHideSearch)
    self.connect(self.txtSearch, QtCore.SIGNAL("textChanged(QString)"), self.doSearch)
    
    self.registerActions(actions)
    registerShortcuts(self.actions, self)
    self.cmb.setFocus()
    self.showHideMessage()
  
  def onLinkClick(self, qurl):
    self.navigate(qurl.toString())

  def registerActions(self, template):
    self.actions["addressnav"]  = [self.navigate, "Enter", self.cmb, "Navigate to the url in the address bar"]
    self.actions["reload"]      = [self.reload, "F5|Ctrl+R", "Reload the current page"]
    self.actions["back"]        = [self.back, "Alt+Left", "Go back in history"]
    self.actions["fwd"]         = [self.fwd, "Alt+Right", "Go forward in history"]
    self.actions["search"]      = [self.showSearch, "/|Ctrl-F", "Search in page"]
    self.actions["smartsearch"] = [self.smartSearch, "F3", "Smart search (find next or start search)"]
    self.actions["stopsearch"]  = [self.stopOrHideSearch, "Escape", self.fraSearch, "Stop current load or searching"]
    self.actions["findnext"]    = [self.doSearch, "Return", self.txtSearch, "Next match for current search"]
    self.actions["togglestatus"]= [self.toggleStatus, "Ctrl+Space", "Toggle visibility of status bar"]

    if template:
      actionnames = list(self.actions.keys())
      for action in template:
        if actionnames.count(action):
          self.actions[action][1] = template[action][1]

  def toggleStatus(self):
    if self.browser:
      self.browser.toggleStatusVisiblity()
    else:
      self.statusbar.setVisible(not self.statusBar.isVisible())

  def setStatusVisibility(self, visible):
    self.statusbar.setVisible(visible)

  def loadContent(self, html, baseUrl = None):
    if baseUrl:
      baseUrl = QtWebKit.QUrl(baseUrl)
    else:
      baseUrl = QtWebKit.QUrl()
    self.webkit.setHTML(html, baseUrl)

  def onUnsupportedContent(self, reply):
    self.log("Unsupported content %s" % (reply.url().toString()))
    if self.browser:
      self.browser.addDownload(reply.url().toString())

  def onDownloadRequested(self, request):
    if self.browser:
      self.browser.addDownload(request.url().toString())

  def doSearch(self, s = None):
    if s is None: s = self.txtSearch.text()
    self.webkit.findText(s, QtWebKit.QWebPage.FindWrapsAroundDocument)

  def stopOrHideSearch(self):
    if self.fraSearch.isVisible():
      self.fraSearch.setVisible(False)
      self.webkit.setFocus()
    else:
      self.webkit.stop()

  def showSearch(self):
    self.txtSearch.setText("")
    self.fraSearch.setVisible(True)
    self.txtSearch.setFocus()

  def zoom(self, lvl):
    self.webkit.setZoomFactor(self.webkit.zoomFactor() + (lvl * 0.25))

  def stop(self):
    self.webkit.stop()

  def URL(self):
    return self.cmb.currentText()

  def loadProgress(self, val):
    if self.pbar.isVisible():
      self.pbar.setValue(val)

  def setTitle(self, title):
    if self.browser:
      self.browser.setTabTitle(self, title)

  def setURL(self, url):
    self.cmb.setEditText(url.toString())

  def refresh(self):
    self.navigate(self.URL())
    self.webkit.reload()

  def loadStarted(self):
    self.showProgressBar()

  def loadFinished(self, success):
    self.hideProgressBar()
    self.setIcon()
    if self.cmb.hasFocus():
      self.webkit.setFocus()
  
  def showProgressBar(self):
    self.pbar.setValue(0)
    self.pbar.setVisible(True)

  def hideProgressBar(self, success = False):
    self.pbar.setVisible(False)

  def setIcon(self):
    if self.browser:
      self.browser.setTabIcon(self, self.webkit.icon())

  def reload(self):
    self.webkit.reload()
  
  def smartSearch(self):
    if self.fraSearch.isVisible():
      self.doSearch()
    else:
      self.showSearch()

  def mkShortcuts(self):
    if self.browser:
      self.bro
  def fwd(self):
    self.webkit.history().forward()

  def back(self):
    self.webkit.history().back()

  def navigate(self, url = None):
    if url and type(url) == str:
      u = url
    else:
      u = str(self.cmb.currentText())
    parts = u.split(":")
    if len(parts) == 2 and parts[0] == "about":
      self.navabout(parts[1].strip().lower())
      return
    if u.strip() == "":
      return
    if self.browser is not None:
      u = self.browser.fixUrl(u)
    self.cmb.setEditText(u)
    if self.browser is not None:
      self.browser.addHistory(u)
    url = QtCore.QUrl(u)
    self.setTitle("Loading...")
    self.webkit.load(url)

  def onStatusBarMessage(self, s):
    if s:
      self.statusbar.showMessage(s)
    else:
      self.showHideMessage()

  def showHideMessage(self):
    self.statusbar.showMessage("(press %s to hide this)" % (self.actions["togglestatus"][1]))

  def onLinkHovered(self, link, title, content):
    if link or title:
      if title and not link:
        self.statusbar.showMessage(title)
      elif link and not title:
        self.statusbar.showMessage(link)
      elif link and title:
        self.statusbar.showMessage("%s (%s)" % (title, link))
    else:
      self.showHideMessage()

  def navabout(self, dst):
    if self.browser is None:
      return
    if dst == "help":
      self.webkit.setHtml(self.browser.genHelp())
      self.cmb.setEditText("about:help")
      return
    elif dst == "foo":
      self.webkit.setHtml(self.browser.genAboutFoo())
      self.cmb.setEditText("about:foo")
      return
    elif dst == "nothing":
      self.webkit.setHtml("")
      self.cmb.setEditText("about:nothing")
      return
    self.webkit.setHtml("<p>Sorry, Jim, that resource cannot be found</p>")
    self.cmb.setEditText("about:lost")

class PrivacyDialog(QtGui.QDialog):
  def __init__(self, parent=None, icon=None):
    QtGui.QDialog.__init__(self, parent)
    if icon:
      self.setWindowIcon(icon)
    self.setWindowTitle("Clear private data")
    self.chkClearCookies  = QtGui.QCheckBox("Clear cookies")
    self.chkClearHistory  = QtGui.QCheckBox("Clear history")
    self.chkClearCache    = QtGui.QCheckBox("Clear cache")
    self.btnOk            = QtGui.QPushButton("OK")
    self.btnCancel        = QtGui.QPushButton("Cancel")
    self.grid = QtGui.QGridLayout(self)
    row = 0
    for chk in [self.chkClearCookies, self.chkClearHistory, self.chkClearCache]:
      self.grid.addWidget(chk, row, 0, 1, 3)
      chk.setChecked(True)
      row += 1
    growrow = row
    row += 1
    self.grid.addWidget(self.btnOk, row, 1)
    self.grid.addWidget(self.btnCancel, row, 2)
    for i in range(self.grid.rowCount()):
      self.grid.setRowStretch(i, 0)
    self.grid.setRowStretch(growrow, 1)
    self.grid.setColumnStretch(0, 1)
    for i in range(self.grid.columnCount()):
      if i:
        self.grid.setColumnStretch(i, 1)
  
    self.connect(self.btnOk, QtCore.SIGNAL("clicked()"), self.accept)
    self.connect(self.btnCancel, QtCore.SIGNAL("clicked()"), self.reject)

class AuthDialog(QtGui.QDialog):
  def __init__(self, parent=None, icon=None):
    QtGui.QDialog.__init__(self, parent)
    if icon:
      self.setWindowIcon(icon)
    self.setWindowTitle("Authentication required")
    self.lblAuth = QtGui.QLabel("Authentication required")
    self.lblUserName = QtGui.QLabel("Username:")
    self.txtUserName = QtGui.QLineEdit()
    self.lblPassword = QtGui.QLabel("Password:")
    self.txtPassword = QtGui.QLineEdit()
    self.txtPassword.setEchoMode(QtGui.QLineEdit.Password)
    self.btnCancel = QtGui.QPushButton("Cancel")
    self.btnOK = QtGui.QPushButton("OK")

    self.grid = QtGui.QGridLayout(self)
    self.grid.addWidget(self.lblAuth, 0, 0, 1, 3)
    self.grid.addWidget(self.lblUserName, 1, 0)
    self.grid.addWidget(self.txtUserName, 1, 1, 1, 3)
    self.grid.addWidget(self.lblPassword, 2, 0)
    self.grid.addWidget(self.txtPassword, 2, 1, 1, 3)
    self.grid.addWidget(self.btnOK, 3, 2)
    self.grid.addWidget(self.btnCancel, 3, 3)

    for i in range(self.grid.columnCount()):
      self.grid.setColumnStretch(i, 0)
    self.grid.setColumnStretch(1, 1)
    for i in range(self.grid.rowCount()):
      self.grid.setRowStretch(i, 0)
    self.cancelled = False
    self.connect(self.btnCancel, QtCore.SIGNAL("clicked()"), self.onCancel)
    self.connect(self.btnOK, QtCore.SIGNAL("clicked()"), self.onOK)

  def onOK(self):
    self.cancelled = False
    self.close()

  def onCancel(self):
    self.cancelled = True
    self.close()

  def prompt(self, url=None):
    self.cancelled = False
    if url:
      self.lblAuth.setText("The page at:\n\n%s\n\nrequires authentication to continue" % (url))
    self.exec_()
    if self.cancelled:
      return None, None
    else:
      return self.txtUserName.text(), self.txtPassword.text()

class MainWin(QtGui.QMainWindow):
  def __init__(self, debug=False):
    QtGui.QMainWindow.__init__(self, None)
    self.downloader = None
    self.debug = debug
    self.actions = dict()
    self.tabactions = dict()
    self.tabactions = dict()
    tmp = WebTab(None, None)
    self.tabactions = tmp.actions
    self.configdir = os.path.join(os.path.expanduser("~"), ".foobrowser")
    self.registerActions()
    self.showStatusBar = False
    self.loadConfig()
    self.icons = Icons()
    self.setWindowIcon(self.icons.QIcon("foobrowser"))
    self.appname = "Foo browser!"
    self.cache_mb = 512
    self.maxHistory = 4096
    self.tabs = []
    self.historyDateFormat = "%Y-%m-%d %H:%M:%S"
    self.maxTitleLen = 40
    if not os.path.isdir(self.configdir):
      try:
        os.mkdir(self.configdir)
      except Exception as e:
        self.configdir = None
    if self.configdir is not None:
      self.loadHistory()
    self.disk_cache = None
    self.cookie_jar = None
    if self.configdir:
      cachedir = os.path.join(self.configdir, "cache")
      if not os.path.isdir(cachedir):
        os.mkdir(cachedir)

      self.disk_cache = QtNetwork.QNetworkDiskCache()
      self.disk_cache.setCacheDirectory(cachedir)
      self.disk_cache.setMaximumCacheSize(self.cache_mb * (1024 * 1024))

      self.cookie_jar = DiskCookies(self.configdir)

    self.auth_cache = dict()
    tmp.deleteLater()
    self.mkGui()
    registerShortcuts(self.actions, self)

  def loadConfig(self):
    if self.configdir:
      if not os.path.isdir(self.configdir):
        try:
          os.mkdir(self.configdir)
        except:
          return
      conffile = os.path.join(self.configdir, "config.ini")
      if not os.path.isfile(conffile):
        return
      try:
        fp = open(conffile, "r")
      except:
        return
      section = ""
      for line in fp:
        line = line.strip()
        if len(line) == 0:
          continue
        if line[0] == "[" and line[-1] == "]":
          section = line.strip("[]")
          continue
        parts = line.split("=")
        if len(parts) < 2:
          continue
        setting = parts[0].strip()
        value = "=".join(parts[1:]).strip()
        self.log("config: %s/%s/%s" % (section, setting, value))
        if section == "shortcuts":
          setting = setting.lower()
          if list(self.actions.keys()).count(setting):
            self.actions[setting][1] = value
          continue
        if section == "tabshortcuts":
          setting = setting.lower()
          if list(self.tabactions.keys()).count(setting):
            self.tabactions[setting][1] = value
          continue
        if section == "general":
          setting = setting.lower()
          if setting == "downloader":
            if value.lower() != "none":
              self.log("setting downloader to %s" % (value))
              self.downloader = value
          elif setting == "showstatus":
            if value.lower() in ["yes", "true", "1"]:
              self.showStatusBar = True
            else:
              self.showStatusBar = False
      fp.close()

  def toggleStatusVisiblity(self):
    self.showStatusBar = not self.showStatusBar
    for t in self.tabs:
      t.setStatusVisibility(self.showStatusBar)

  def persistConfig(self):
    if self.configdir:
      if not os.path.isdir(self.configdir):
        try:
          os.mkdir(self.configdir)
        except:
          return
      conffile = os.path.join(self.configdir, "config.ini")
      try:
        fp = open(conffile, "w")
      except:
        return
      # write out shortcuts
      fp.write("[general]\n")
      fp.write("; general settings\n")
      if self.downloader:
        fp.write("downloader = %s\n" % (str(self.downloader)))
      else:
        fp.write("downloader = None\n")
      if self.showStatusBar:
        fp.write("showstatus = True\n")
      else:
        fp.write("showstatus = False\n")
      fp.write("[shortcuts]\n")
      fp.write("; shortcuts applied to the application as a whole\n")
      actionnames = list(self.actions.keys())
      actionnames.sort()
      for action in actionnames:
        fp.write("%s = %s\n" % (action, self.actions[action][1]))
      fp.write("[tabshortcuts]\n")
      fp.write("; shortcuts applied to individual tabs\n")
      actionnames = list(self.tabactions.keys())
      actionnames.sort()
      for action in actionnames:
        fp.write("%s = %s\n" % (action, self.tabactions[action][1]))
      fp.close()

  def registerActions(self):
    self.actions["newwin"]    = [self.addWin,       "Ctrl+N", "Open new window"]
    self.actions["newtab"]    = [self.addTab,       "Ctrl+T", "Open new tab"]
    self.actions["closetab"]  = [self.delTab,       "Ctrl+W", "Close current tab"]
    self.actions["tabprev"]   = [self.decTab,       "Ctrl+PgUp", "Switch to previous tab"]
    self.actions["tabnext"]   = [self.incTab,       "Ctrl+PgDown", "Switch to next tab"]
    self.actions["go"]        = [self.currentTabGo, "Ctrl+G", "Focus address bar"]
    self.actions["close"]     = [self.close,        "Ctrl+Q", "Close application"]
    self.actions["zoomin"]    = [self.zoomIn,       "Ctrl+Up", "Zoom into page"]
    self.actions["zoomout"]   = [self.zoomOut,      "Ctrl+Down", "Zoom out of page"]
    self.actions["help"]      = [self.showHelp,     "F1", "Show this help page"]
    self.actions["cleardata"] = [self.clearData,    "Ctrl+Shift+Delete", "Clear cache and private data"]

  def clearData(self):
    dlg = PrivacyDialog(parent=self, icon=self.icons.QIcon("foobrowser"))
    if dlg.exec_() == QtGui.QDialog.Accepted:
      if dlg.chkClearCookies.isChecked() and self.cookie_jar:
        self.cookie_jar.clear()
      if dlg.chkClearCache.isChecked() and self.disk_cache:
        self.disk_cache.clear()
      if dlg.chkClearHistory.isChecked():
        self.history = {}

  def showHelp(self):
    self.addTab().navigate("about:help")

  def addWin(self):
    MainWin().show()

  def currentTabGo(self):
    self.tabs[self.tabWidget.currentIndex()].cmb.setFocus()

  def zoomIn(self):
    self.zoom(1)
  def zoomOut(self):
    self.zoom(-1)

  def zoom(self, lvl):
    self.tabs[self.tabWidget.currentIndex()].zoom(lvl)
    
  def decTab(self):
    self.incTab(-1)

  def incTab(self, incby = 1):
    if self.tabWidget.count() < 2:
      return
    idx = self.tabWidget.currentIndex()
    idx += incby
    if idx < 0:
      idx = self.tabWidget.count()-1;
    elif idx >= self.tabWidget.count():
      idx = 0
    self.tabWidget.setCurrentIndex(idx)

  def setTabIcon(self, tab, icon):
    idx = self.getTabIndex(tab)
    if idx > -1:
      self.tabWidget.setTabIcon(idx, icon)

  def setTabTitle(self, tab, title):
    idx = self.getTabIndex(tab)
    if idx > -1:
      if len(title) > self.maxTitleLen:
        title = title[:self.maxTitleLen-3] + "..."
      self.tabWidget.setTabText(idx, title)

  def getTabIndex(self, tab):
    for i in range(len(self.tabs)):
      if tab == self.tabs[i]:
        return i
    return -1

  def setupWebkit(self, webkit):
    nam = webkit.page().networkAccessManager()
    nam.authenticationRequired.connect(self.onAuthRequest)
    nam.setCache(self.disk_cache)
    nam.setCookieJar(self.cookie_jar)
    self.cookie_jar.setParent(None)
    self.disk_cache.setParent(None)
    g = webkit.settings()
    g.enablePersistentStorage(self.configdir)

  def onAuthRequest(self, networkreply, authenticator):
    cached = list(self.auth_cache.keys())
    r = authenticator.realm()
    if cached.count(r):
      authenticator.setUser(self.auth_cache[r]["user"])
      authenticator.setPassword(self.auth_cache[r]["password"])
    else:
      authdlg = AuthDialog(parent=self, icon=self.icons.QIcon("foobrowser"))
      username, password = authdlg.prompt(networkreply.url().toString())
      if username and password:
        authenticator.setUser(username)
        authenticator.setPassword(password)
        self.auth_cache[r] = {"user":username, "password":password}

  def closeEvent(self, e):
    if len(self.tabs) > 1:
      if QtGui.QMessageBox.question(self, "Confirm exit", "You have more than one tab open. Are you sure you want to exit?", QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) == QtGui.QMessageBox.No:
        e.ignore()
        return
    self.persistHistory()
    self.persistConfig()
    if self.disk_cache:
      self.disk_cache.expire()
    if self.cookie_jar:
      self.cookie_jar.Persist()
    e.accept()
    self.close()

  def log(self, s):
    if self.debug:
      print(s)

  def persistHistory(self):
    if self.configdir is None:
      return
    hfile = os.path.join(self.configdir, "history")
    try:
      fp = open(hfile, "w")
    except Exception as e:
      return
    keys = list(self.history.keys())
    keys.sort()
    for k in keys[:self.maxHistory]:    # only store up to the last maxHistory history points
      fp.write("%s :: %s\n" % (time.strftime(self.historyDateFormat, k), self.history[k])) 
    fp.close()

  def loadHistory(self):
    self.history = {}
    if self.configdir is None:
      return
    hfile = os.path.join(self.configdir, "history")
    if os.path.isfile(hfile):
      for line in open(hfile, "r"):
        line = line.strip()
        parts = line.split("::")
        try:
          k = time.strptime(parts[0].strip(), self.historyDateFormat)
          hurl = "::".join(parts[1:]).strip()
          self.history[k] = hurl
        except Exception as e:
          self.log(str(e))
          pass

  def LoadHistoryToCmb(self, cmb):
    if self.configdir is None:
      return
    keys = list(self.history.keys())
    keys.sort(reverse=True)
    if keys:
      cmb.addItem("")
    items = []
    for k in keys:
      if self.history[k] in items:
        continue
      cmb.addItem(self.history[k])
      items.append(self.history[k])
    if keys:
      cmb.setCurrentIndex(0)

  def addHistory(self, url, when = None):
    if when is None:
      when = time.localtime()
    self.history[when] = url

  def mkGui(self):
    self.layout().setSpacing(1)
    self.setWindowTitle(self.appname)
    self.tabWidget = QtGui.QTabWidget(self)
    self.tabWidget.tabBar().setMovable(True)
    self.tabWidget.setStyleSheet("padding: 2px; margin: 2px;")
    self.setCentralWidget(self.tabWidget)
    self.tabWidget.setTabsClosable(True)

    self.connect(self.tabWidget, QtCore.SIGNAL("tabCloseRequested(int)"), self.delTab)
    self.connect(self, QtCore.SIGNAL("refreshAll()"), self.refreshAll)
    self.addTab()

  def addTab(self, url = None):
    tab = WebTab(browser=self, actions=self.tabactions, showStatusBar = self.showStatusBar)
    self.tabWidget.addTab(tab, "New tab")
    self.tabs.append(tab)
    self.tabWidget.setCurrentWidget(tab)
    if url:
      tab.navigate(url)
    else:
      self.currentTabGo()
    return self.tabs[self.tabWidget.currentIndex()]
  
  def addDownload(self, url):
    if type(self.downloader) == str:
# commandline
      cmd = self.downloader.replace("%url%", "\"%s\"" % url)
      retcode = subprocess.call(cmd)
      if retcode:
        if (QtGui.QMessageBox.question(self, "External downloader failure", "An attempt to invoke your external downloader with the command line:\n\n%s\n\nappears to have failed. Would you like to change the commandline to your external downloader?" % (cmd)) == QtGui.QMessageBox.Ok):
          self.downloader = None
          self.addDownload(url)
    elif self.downloader is None:
# prompt the user
      dlg = QtGui.QInputDialog()
      lbltxt = "%s does not implement an internal download manager but will talk to external download managers which can be command-line driven.\n\nPlease enter a commandline for an external downloader. %%url%% in your command will be replaced with the url to download" % (self.appname)
      commandline, ok = dlg.getText(self, "External downloader configuration", lbltxt)
      commandline = commandline.strip()
      if commandline == "" or ok == False:
        if QtGui.QMessageBox.question(self, "External downloader problem", "You haven't specified an external downloader command line. This means the request to download %s can't be processed. Are you sure?" % (url), QtGui.QMessageBox.Yes, QtGui.QMessageBox.No) == QtGui.QMessageBox.Yes:
          return
        self.addDownload(url)
      self.downloader = commandline
      self.addDownload(url)

  def fixUrl(self, url):
    # look for "smart" google search
    search = False
    parts = url.split("://")
    if len(parts) != 2 or (len(parts) == 2 and parts[0] not in ["http", "https", "ftp"]):
      parts = url.split(" ")  # multipl words == search
      if len(parts) > 1:
        search = True
      hostname = url.split("/")[0]
      parts = hostname.split(".")  # hostname without periods == perhaps search
      if len(parts) == 1:
        try:
          socket.gethostbyname(hostname) # if we can look up the host name, go for it
        except:
          search = True
    if search:
      url = "http://www.google.com/search?q=%s" % (url.replace(" ", "+"))
    else:
      try:
        if url.index("about:") == 0:
          return url
      except:
        if url.count("://") == 0:
          url = "%s%s" % ("http://", url)
    return url

  def delTab(self, idx = -1):
    if idx >= len(self.tabs):
      return
    if idx == -1:
      idx = self.tabWidget.currentIndex()
    t = self.tabs.pop(idx)
    t.stop()
    self.tabWidget.removeTab(idx)
    t.deleteLater()
    if len(self.tabs) == 0:
      self.close()

  def load(self, url):
    if self.tabs[-1].URL() == "":
      self.tabs[-1].navigate(url)
    else:
      self.addTab(url)

  def refreshAll(self):
    for t in self.tabs:
      t.refresh()

  def defaultCSS(self):
    return " html {background-color: Window, color: WindowText}\ntable {border-collapse: collapse; margin: auto;}\ntd,th {border: 1px solid ThreeDDarkShadow; padding-left: 5px; padding-right: 5px}\n h1,h2,h3,h4,h5 {text-align: center;}"

  def genAboutFoo(self):
    return "<html><head><title>About %s</title><style>%s</style></head><body><h4>About %s</h4><p>%s is a dead-simple, lightweight tabbed web browser with support for:</p><ul><li>Disk cache</li><li>Persistent cookies</li><li>Plugin support (eg flash), where WebKit supports it</li><li>Re-orderable tabs</li><li>Browsing history (max %i items)</li><li>External download manager</li><li>Basic authentication for websites that require authentication</li></ul><p>%s would have been completely impossible without the giants upon whose shoulders it stands:</p><ul><li>Python</li><li>Qt (and PyQt4 in particular)</li><li>And, of course, Webkit</li></ul><p>%s was started as a fun project just to see what would be involved in creating a light browser out of the available powerful components. I hope that you find it useful!</p><p>Author: Davyd McColl (<a href=\"mailto:davydm@gmail.com\">davydm@gmail.com</a>)</body></html>" % (self.appname, self.appname, self.appname, self.appname, self.maxHistory, self.appname, self.appname)

  def genHelp(self):
    ret = ["<html><head><title>Help for: %s</title><style>%s</style></head><body><h4>Help for: <a href=\"about:foo\">%s</a></h4>" % (self.appname, self.defaultCSS(), self.appname)]
    ret.extend(self.genActionTable(self.actions, "Application shortcuts"))
    ret.append("<br/>")
    ret.extend(self.genActionTable(self.tabactions, "Tab shortcuts"))
    ret.append("</body></html>")
    return "".join(ret)

  def genActionTable(self, actions, title):
    ret = []
    ret.append("<h5>%s</h5><table>" % (title))
    ret.append("<tr><th>Action</th><th>Shortcut</th></tr>")
    data = {}
    for action in actions:
      shortcut = None
      description = None
      # each item is either a list of 3 elements:
#         bound method, shortcut key, description
#       or:
#         bound method, shortcut key, bound object, description
      shortcut = actions[action][1]
      if len(actions[action]) == 3:
        description = actions[action][2]
      elif len(actions[action]) == 4:
        description = actions[action][3]
      if shortcut and description:
        data[description] = shortcut

    d = list(data.keys())
    d.sort()
    for desc in d:
      ret.append("<tr><td>%s</td><td>%s</td></tr>" % (desc, data[desc]))
    ret.append("</table>")
    return ret


if __name__ == "__main__":
  app = QtGui.QApplication([])
  debug = False
  if sys.argv[1:].count("-debug"):
    debug = True
  mainwin = MainWin(debug=debug)
  mainwin.show()
  for arg in sys.argv[1:]:
    if arg not in ["-debug"]:
      mainwin.load(arg)
  app.exec_()
