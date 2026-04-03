import { initializeApp, getApps, getApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider } from 'firebase/auth'

const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY             || "AIzaSyB7Eb7VJbY6hGGLeVzFNCT8lrOPHGCk5k8",
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN         || "hapura-hq.firebaseapp.com",
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID          || "hapura-hq",
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET      || "hapura-hq.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "553138370139",
  appId:             import.meta.env.VITE_FIREBASE_APP_ID              || "1:553138370139:web:d251766085a059916ef17e",
}

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp()
export const auth = getAuth(app)
export const googleProvider = new GoogleAuthProvider()
