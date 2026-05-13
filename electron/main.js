const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('path');

const SERVER_URL = 'https://pic.xhs365.cn';

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'ArtForge AI',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webviewTag: false,
    },
    titleBarStyle: 'default',
    show: false,
  });

  mainWindow.loadURL(SERVER_URL);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  const template = [
    {
      label: '操作',
      submenu: [
        { label: '刷新', accelerator: 'CmdOrCtrl+R', click: () => mainWindow.reload() },
        { label: '强制刷新', accelerator: 'CmdOrCtrl+Shift+R', click: () => mainWindow.webContents.reloadIgnoringCache() },
        { type: 'separator' },
        { label: '全屏', accelerator: 'F11', click: () => mainWindow.setFullScreen(!mainWindow.isFullScreen()) },
        { type: 'separator' },
        { label: '退出', accelerator: 'CmdOrCtrl+Q', click: () => app.quit() },
      ],
    },
    {
      label: '帮助',
      submenu: [
        { label: '关于 ArtForge AI', click: () => shell.openExternal(SERVER_URL) },
        { label: '查看定价', click: () => mainWindow.loadURL(SERVER_URL + '/#pricing') },
      ],
    },
  ];

  if (process.env.NODE_ENV === 'development') {
    template.push({
      label: '开发者',
      submenu: [
        { label: '开发者工具', accelerator: 'F12', click: () => mainWindow.webContents.toggleDevTools() },
      ],
    });
  }

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, url) => {
    event.preventDefault();
    shell.openExternal(url);
  });
});
