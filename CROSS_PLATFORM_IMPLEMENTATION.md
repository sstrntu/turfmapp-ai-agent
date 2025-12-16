# Cross-Platform Implementation Guide

This guide provides step-by-step instructions for extending your TurfmApp AI Agent to desktop (Mac) and mobile (iPhone) platforms while maintaining a single codebase.

## Table of Contents
1. [Current Architecture Analysis](#current-architecture-analysis)
2. [Cross-Platform Strategy](#cross-platform-strategy)
3. [Desktop Implementation (Mac App)](#desktop-implementation-mac-app)
4. [Mobile Implementation (iPhone App)](#mobile-implementation-iphone-app)
5. [Implementation Timeline](#implementation-timeline)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Current Architecture Analysis

### ✅ Strengths for Cross-Platform
- **Backend**: FastAPI (Python) - Platform agnostic REST API
- **Frontend**: React + Vite - Highly portable web components  
- **Database**: Supabase - Cloud-native, accessible from any platform
- **AI Integration**: LlamaIndex + OpenAI/Anthropic - API-based
- **Authentication**: JWT + OAuth - Standard web protocols

### 📁 Current Structure
```
turfmapp-ai-agent/
├── backend/           # FastAPI server (shared by all platforms)
├── frontend/          # React web app
├── docker-compose.yml # Current deployment
└── README.md
```

---

## Cross-Platform Strategy

### Single Repo Approach
Keep everything in one repository with platform-specific build targets:

```
turfmapp-ai-agent/
├── backend/           # Shared FastAPI backend
├── frontend/          # Shared React frontend  
├── desktop/           # Electron wrapper
├── mobile/           # Capacitor wrapper
└── scripts/          # Cross-platform build scripts
```

### Platform Deployment Matrix
| Platform | Technology | Effort Level | Timeline | Code Reuse |
|----------|-----------|--------------|----------|------------|
| Web      | Current   | ✅ Done      | -        | 100%       |
| Mac App  | Electron  | 🟡 Medium    | 2-3 weeks| 95%        |
| iPhone   | Capacitor | 🔴 High      | 4-6 weeks| 85%        |

---

## Desktop Implementation (Mac App)

### Phase 1: Electron Setup (Week 1)

#### 1.1 Install Dependencies
```bash
cd frontend
npm install --save-dev electron electron-builder electron-dev
npm install --save electron-updater
```

#### 1.2 Create Electron Main Process
Create `frontend/desktop/main.js`:
```javascript
const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
const { autoUpdater } = require('electron-updater');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development';

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset', // macOS style
    icon: path.join(__dirname, '../public/icons/app-icon.png')
  });

  const startUrl = isDev 
    ? 'http://localhost:3005' 
    : `file://${path.join(__dirname, '../dist/index.html')}`;
  
  mainWindow.loadURL(startUrl);

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Auto-updater
if (!isDev) {
  autoUpdater.checkForUpdatesAndNotify();
}
```

#### 1.3 Create Preload Script
Create `frontend/desktop/preload.js`:
```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  versions: process.versions,
  openExternal: (url) => ipcRenderer.invoke('open-external', url)
});
```

#### 1.4 Update Package.json
Add to `frontend/package.json`:
```json
{
  "main": "desktop/main.js",
  "homepage": "./",
  "scripts": {
    "electron": "NODE_ENV=development electron .",
    "electron:dev": "concurrently \"npm run dev\" \"wait-on http://localhost:3005 && electron .\"",
    "electron:build": "npm run build && electron-builder",
    "electron:dist": "npm run build && electron-builder --publish=never"
  },
  "devDependencies": {
    "concurrently": "^7.6.0",
    "wait-on": "^7.0.1"
  },
  "build": {
    "appId": "com.turfmapp.ai-agent",
    "productName": "TurfmApp AI",
    "directories": {
      "output": "dist-electron"
    },
    "files": [
      "dist/**/*",
      "desktop/**/*",
      "node_modules/**/*"
    ],
    "mac": {
      "category": "public.app-category.productivity",
      "target": "dmg",
      "icon": "public/icons/app-icon.icns"
    }
  }
}
```

### Phase 2: Desktop-Specific Features (Week 2)

#### 2.1 Native Menu Bar
Create `frontend/desktop/menu.js`:
```javascript
const { Menu, shell, app } = require('electron');

const template = [
  {
    label: 'TurfmApp',
    submenu: [
      { label: 'About TurfmApp', role: 'about' },
      { type: 'separator' },
      { label: 'Hide TurfmApp', accelerator: 'Command+H', role: 'hide' },
      { label: 'Hide Others', accelerator: 'Command+Shift+H', role: 'hideothers' },
      { label: 'Show All', role: 'unhide' },
      { type: 'separator' },
      { label: 'Quit', accelerator: 'Command+Q', click: () => app.quit() }
    ]
  },
  {
    label: 'Edit',
    submenu: [
      { label: 'Undo', accelerator: 'CmdOrCtrl+Z', role: 'undo' },
      { label: 'Redo', accelerator: 'Shift+CmdOrCtrl+Z', role: 'redo' },
      { type: 'separator' },
      { label: 'Cut', accelerator: 'CmdOrCtrl+X', role: 'cut' },
      { label: 'Copy', accelerator: 'CmdOrCtrl+C', role: 'copy' },
      { label: 'Paste', accelerator: 'CmdOrCtrl+V', role: 'paste' }
    ]
  },
  {
    label: 'View',
    submenu: [
      { label: 'Reload', accelerator: 'CmdOrCtrl+R', role: 'reload' },
      { label: 'Force Reload', accelerator: 'CmdOrCtrl+Shift+R', role: 'forceReload' },
      { label: 'Toggle Developer Tools', accelerator: 'F12', role: 'toggleDevTools' },
      { type: 'separator' },
      { label: 'Actual Size', accelerator: 'CmdOrCtrl+0', role: 'resetZoom' },
      { label: 'Zoom In', accelerator: 'CmdOrCtrl+Plus', role: 'zoomIn' },
      { label: 'Zoom Out', accelerator: 'CmdOrCtrl+-', role: 'zoomOut' },
      { type: 'separator' },
      { label: 'Toggle Fullscreen', accelerator: 'Ctrl+Command+F', role: 'togglefullscreen' }
    ]
  }
];

module.exports = Menu.buildFromTemplate(template);
```

#### 2.2 System Tray Integration
Add to `frontend/desktop/main.js`:
```javascript
const { Tray, nativeImage } = require('electron');

let tray = null;

function createTray() {
  const icon = nativeImage.createFromPath(path.join(__dirname, '../public/icons/tray-icon.png'));
  tray = new Tray(icon.resize({ width: 16, height: 16 }));
  
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show TurfmApp', click: () => mainWindow.show() },
    { label: 'Quit', click: () => app.quit() }
  ]);
  
  tray.setToolTip('TurfmApp AI Agent');
  tray.setContextMenu(contextMenu);
  
  tray.on('click', () => {
    mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
  });
}
```

### Phase 3: Build & Distribution (Week 3)

#### 3.1 Create App Icons
Create icons in multiple sizes:
- `frontend/public/icons/app-icon.icns` (Mac)
- `frontend/public/icons/tray-icon.png` (16x16)
- Generate using: https://iconverticons.com/online/

#### 3.2 Build Scripts
Create `scripts/build-desktop.sh`:
```bash
#!/bin/bash
set -e

echo "Building desktop app..."
cd frontend

# Build web assets
npm run build

# Build Electron app
npm run electron:dist

echo "Desktop app built successfully!"
echo "Output: frontend/dist-electron/"
```

#### 3.3 Code Signing (for distribution)
Add to `frontend/package.json` build config:
```json
{
  "build": {
    "mac": {
      "hardenedRuntime": true,
      "entitlements": "desktop/entitlements.mac.plist",
      "entitlementsInherit": "desktop/entitlements.mac.plist"
    },
    "afterSign": "desktop/notarize.js"
  }
}
```

---

## Mobile Implementation (iPhone App)

### Phase 1: Capacitor Setup (Weeks 1-2)

#### 1.1 Install Capacitor
```bash
cd frontend
npm install @capacitor/core @capacitor/cli
npm install @capacitor/ios
npx cap init turfmapp-ai com.turfmapp.ai
```

#### 1.2 Configure Capacitor
Update `frontend/capacitor.config.ts`:
```typescript
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.turfmapp.ai',
  appName: 'TurfmApp AI',
  webDir: 'dist',
  bundledWebRuntime: false,
  server: {
    androidScheme: 'https'
  },
  ios: {
    contentInset: 'automatic',
    scrollEnabled: true,
    backgroundColor: '#000000'
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#000000',
      showSpinner: false
    },
    StatusBar: {
      style: 'dark',
      backgroundColor: '#000000'
    }
  }
};

export default config;
```

#### 1.3 Add iOS Platform
```bash
npx cap add ios
npx cap sync
```

### Phase 2: Mobile-Optimized UI (Weeks 2-3)

#### 2.1 Responsive CSS Updates
Create `frontend/src/styles/mobile.css`:
```css
@media (max-width: 768px) {
  .app-container {
    padding: 0;
    height: 100vh;
    height: 100dvh; /* Dynamic viewport height */
  }

  .chat-input {
    padding: 12px;
    font-size: 16px; /* Prevent zoom on iOS */
  }

  .message-bubble {
    max-width: calc(100% - 40px);
    margin: 8px 20px;
  }

  /* Safe area handling */
  .app-header {
    padding-top: env(safe-area-inset-top);
  }

  .app-footer {
    padding-bottom: env(safe-area-inset-bottom);
  }
}
```

#### 2.2 Touch Optimizations
Update `frontend/src/components/ChatThread.jsx`:
```jsx
import { useEffect } from 'react';

export default function ChatThread() {
  useEffect(() => {
    // Prevent zoom on double tap
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function (event) {
      const now = (new Date()).getTime();
      if (now - lastTouchEnd <= 300) {
        event.preventDefault();
      }
      lastTouchEnd = now;
    }, false);

    // Prevent overscroll
    document.body.addEventListener('touchmove', function(event) {
      if (event.scale !== 1) {
        event.preventDefault();
      }
    }, { passive: false });
  }, []);

  // ... rest of component
}
```

### Phase 3: iOS-Specific Features (Weeks 3-4)

#### 3.1 Push Notifications
```bash
npm install @capacitor/push-notifications
```

Add to `frontend/src/mobile/notifications.js`:
```javascript
import { PushNotifications } from '@capacitor/push-notifications';

export async function setupPushNotifications() {
  // Request permission
  let permStatus = await PushNotifications.checkPermissions();
  
  if (permStatus.receive === 'prompt') {
    permStatus = await PushNotifications.requestPermissions();
  }
  
  if (permStatus.receive !== 'granted') {
    throw new Error('User denied permissions!');
  }
  
  await PushNotifications.register();
}
```

#### 3.2 Native Storage
```bash
npm install @capacitor/preferences
```

Update storage utilities:
```javascript
import { Preferences } from '@capacitor/preferences';

export const storage = {
  async setItem(key, value) {
    await Preferences.set({ key, value: JSON.stringify(value) });
  },
  
  async getItem(key) {
    const { value } = await Preferences.get({ key });
    return value ? JSON.parse(value) : null;
  },
  
  async removeItem(key) {
    await Preferences.remove({ key });
  }
};
```

### Phase 4: Build & App Store (Weeks 4-6)

#### 4.1 Build for iOS
```bash
npm run build
npx cap sync ios
npx cap open ios
```

#### 4.2 Xcode Configuration
In Xcode:
1. Set bundle identifier: `com.turfmapp.ai`
2. Add app icons (all required sizes)
3. Configure privacy usage descriptions in `Info.plist`:
```xml
<key>NSCameraUsageDescription</key>
<string>This app uses the camera to capture images for AI analysis.</string>
<key>NSMicrophoneUsageDescription</key>
<string>This app uses the microphone for voice input.</string>
```

#### 4.3 Build Scripts
Create `scripts/build-mobile.sh`:
```bash
#!/bin/bash
set -e

echo "Building mobile app..."
cd frontend

# Build web assets
npm run build

# Sync with Capacitor
npx cap sync ios

echo "Mobile app synced. Open ios/TurfmappAI.xcworkspace in Xcode"
```

---

## Implementation Timeline

### Recommended Phases

#### Phase 1: Desktop (Mac) - 3 weeks
- **Week 1**: Basic Electron setup, window management
- **Week 2**: Native features (menu, tray, shortcuts)  
- **Week 3**: Build pipeline, code signing, testing

#### Phase 2: Mobile (iPhone) - 6 weeks
- **Week 1-2**: Capacitor setup, basic iOS build
- **Week 3-4**: Mobile UI optimizations, touch handling
- **Week 5-6**: Native features, App Store preparation

### Resource Requirements
- **Developer time**: 1 developer, 9 weeks total
- **Additional costs**: 
  - Apple Developer Account ($99/year)
  - Code signing certificate (if distributing outside App Store)
  - TestFlight for beta testing (included with Apple Developer)

---

## Best Practices

### Code Organization
```
frontend/
├── src/
│   ├── components/        # Shared React components
│   ├── hooks/            # Platform-aware hooks
│   ├── utils/            # Platform utilities
│   └── platforms/
│       ├── web.js        # Web-specific code
│       ├── desktop.js    # Electron-specific code
│       └── mobile.js     # Capacitor-specific code
├── desktop/              # Electron main process
├── mobile/               # Capacitor config & plugins
└── public/
    ├── icons/            # All platform icons
    └── splash/           # Mobile splash screens
```

### Platform Detection
Create `frontend/src/utils/platform.js`:
```javascript
export const isElectron = () => 
  typeof window !== 'undefined' && window.electronAPI;

export const isCapacitor = () =>
  typeof window !== 'undefined' && window.Capacitor;

export const isMobile = () =>
  isCapacitor() || /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

export const isDesktop = () => isElectron();

export const isWeb = () => !isElectron() && !isCapacitor();
```

### Shared API Client
Keep backend communication consistent:
```javascript
// frontend/src/api/client.js
const API_BASE = process.env.VITE_BACKEND_URL || 'http://localhost:8000';

export class ApiClient {
  constructor() {
    this.baseUrl = API_BASE;
  }

  async fetch(endpoint, options = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  }
}
```

---

## Troubleshooting

### Common Electron Issues

#### Build Fails on macOS
```bash
# Clear electron cache
rm -rf ~/.electron
rm -rf node_modules
npm install
```

#### App Won't Start
Check `desktop/main.js` paths:
```javascript
// Use __dirname for relative paths
const preloadPath = path.join(__dirname, 'preload.js');
```

### Common Capacitor Issues

#### iOS Build Fails
1. Check Xcode version compatibility
2. Clean build folder: Product → Clean Build Folder
3. Update iOS deployment target in Xcode

#### App Crashes on Device
1. Check Safari Web Inspector for errors
2. Ensure all network requests use HTTPS
3. Test on iOS Simulator first

### Backend Considerations

#### CORS Configuration
Update `backend/app/main.py` for mobile access:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3005",  # Web dev
        "capacitor://localhost",  # iOS
        "https://localhost",      # Desktop
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Content Security Policy
For production builds, update CSP headers:
```python
# Allow connections from native apps
csp_policy = (
    "default-src 'self'; "
    "connect-src 'self' capacitor: https:; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline';"
)
```

---

## Next Steps

After implementation:

1. **Testing Strategy**
   - Unit tests for platform utilities
   - E2E tests on each platform
   - Device testing on real iOS devices

2. **Distribution**
   - Mac: Direct download, Mac App Store, or Homebrew
   - iOS: TestFlight beta → App Store release

3. **Monitoring**
   - Platform-specific analytics
   - Crash reporting (Sentry, Bugsnag)
   - Performance monitoring

4. **Updates**
   - Electron: Auto-updater setup
   - iOS: App Store review process
   - Web: Standard deployment pipeline

---

This guide provides everything needed to extend your TurfmApp to desktop and mobile while maintaining code quality and user experience across all platforms.