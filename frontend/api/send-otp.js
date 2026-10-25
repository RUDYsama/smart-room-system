import nodemailer from 'nodemailer';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const authHeader = req.headers['x-relay-secret'];
  if (authHeader !== 'smart-room-otp-relay-secret-2026') {
    return res.status(401).json({ error: 'Unauthorized relay access' });
  }

  const { to, subject, html, text } = req.body || {};
  if (!to || !subject) {
    return res.status(400).json({ error: 'Missing required fields: to, subject' });
  }

  try {
    const transporter = nodemailer.createTransport({
      host: 'smtp.gmail.com',
      port: 587,
      secure: false,
      auth: {
        user: 'rtaxdt@gmail.com',
        pass: 'trqbrkhvayuwyckj',
      },
      tls: {
        rejectUnauthorized: false,
      },
      connectionTimeout: 10000,
      greetingTimeout: 10000,
      socketTimeout: 10000,
    });

    const info = await transporter.sendMail({
      from: '"ระบบบริหารจัดการและจองสถานที่อัจฉริยะ" <rtaxdt@gmail.com>',
      to: to,
      subject: subject,
      text: text || '',
      html: html || '',
    });

    return res.status(200).json({
      success: true,
      messageId: info.messageId,
      accepted: info.accepted,
    });
  } catch (error) {
    console.error('Vercel SMTP Relay error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'SMTP relay failed',
    });
  }
}
