import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider } from 'firebase/auth'

const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY             || "AIzaSyDg2-J2J968oeKcbn08aieV6o-RqdJyVJQ",
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN         || "trendkr-hapura.firebaseapp.com",
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID          || "trendkr-hapura",
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET      || "trendkr-hapura.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "635022569271",
  appId:             import.meta.env.VITE_FIREBASE_APP_ID              || "1:635022569271:web:f43f874cc250b402e8f4b2",
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const googleProvider = new GoogleAuthProvider()
