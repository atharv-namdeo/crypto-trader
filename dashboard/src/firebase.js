// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

// Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyBtkOrp9Iizskp9-7KmFS8SsPpEMFWkfSs",
    authDomain: "quant-ac5b9.firebaseapp.com",
    projectId: "quant-ac5b9",
    storageBucket: "quant-ac5b9.firebasestorage.app",
    messagingSenderId: "229378767288",
    appId: "1:229378767288:web:7a677c60c73ff2eb7e774d",
    measurementId: "G-4NNBXEP9L9"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);