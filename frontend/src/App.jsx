import React, { useEffect } from 'react';

export default function App() {
  useEffect(() => {
    window.location.replace('https://smart-room-system-5vh7.onrender.com/user/');
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0a0e17',
      color: '#fff',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'sans-serif'
    }}>
      <p>กำลังนำทางเข้าสู่ระบบ VH Smart Room & Hotel Reservation System...</p>
    </div>
  );
}
