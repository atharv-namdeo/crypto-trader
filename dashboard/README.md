# Crypto Algo Trader Dashboard

This is the front-end dashboard for the Crypto Algo Trader bot, built with Vite, React, Tailwind CSS v3, Recharts, and Firebase.

## Setup Instructions

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Configure Firebase**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a web app in your project to get your configuration object.
   - Open `src/firebase.js` and replace the placeholder configuration with your actual Firebase credentials.

3. **Run Development Server**
   ```bash
   npm run dev
   ```
   *The dashboard will start at http://localhost:5173*.

## Deployment to Firebase Hosting (Phase 6)

1. **Build the Project**
   ```bash
   npm run build
   ```

2. **Install Firebase CLI Tools (if you haven't yet)**
   ```bash
   npm install -g firebase-tools
   ```

3. **Login and Initialize**
   ```bash
   firebase login
   firebase init hosting
   ```
   *When prompted:*
   - Choose your `crypto-trader` project.
   - For public directory, type `dist`.
   - Configure as a single-page app: `Yes`.
   - Set up automatic builds: `No`.

4. **Deploy**
   ```bash
   firebase deploy --only hosting
   ```
   *Your live dashboard URL will be provided in the terminal.*
