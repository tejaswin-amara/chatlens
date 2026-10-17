import {
  getCaptcha,
  loginAndFetchSemesters,
  fetchAttendanceData,
} from '../src/lib/scrapers/attendance';

async function diagnose() {
  try {
    console.log('=== STEP 1: Fetching CAPTCHA ===');
    const { captchaImage, session } = await getCaptcha();
    console.log('CSRF token:', session.csrfToken.slice(0, 20) + '...');
    console.log('Cookies:', session.cookies.length, 'cookies');
    console.log('Captcha image length:', captchaImage.length);

    const apiKey = process.env.OCR_SPACE_API_KEY || 'helloworld';
    const cleanBase64 = captchaImage
      .replace(/^data:image\/[a-z]+;base64,/, '')
      .replace(/[\r\n\s]/g, '');
    const formData = new URLSearchParams();
    formData.append('base64Image', `data:image/png;base64,${cleanBase64}`);
    formData.append('OCREngine', '2');
    const ocrRes = await fetch('https://api.ocr.space/parse/image', {
      method: 'POST',
      headers: {
        apikey: apiKey,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
      signal: AbortSignal.timeout(10000),
    });
    const ocrJson = await ocrRes.json();
    const ocrText = ocrJson?.ParsedResults?.[0]?.ParsedText || '';
    let solvedCaptcha = ocrText
      .trim()
      .toLowerCase()
      .replace(/[^a-z]/g, '');
    console.log('OCR Engine2 raw:', JSON.stringify(ocrText));
    console.log('OCR Engine2 solved:', solvedCaptcha);

    if (!solvedCaptcha || solvedCaptcha.length < 3) {
      console.log('Engine 2 failed, trying engine 1...');
      const formData2 = new URLSearchParams();
      formData2.append('base64Image', `data:image/png;base64,${cleanBase64}`);
      formData2.append('OCREngine', '1');
      const ocrRes2 = await fetch('https://api.ocr.space/parse/image', {
        method: 'POST',
        headers: {
          apikey: apiKey,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData2.toString(),
        signal: AbortSignal.timeout(10000),
      });
      const ocrJson2 = await ocrRes2.json();
      const ocrText2 = ocrJson2?.ParsedResults?.[0]?.ParsedText || '';
      const solved2 = ocrText2
        .trim()
        .toLowerCase()
        .replace(/[^a-z]/g, '');
      console.log('OCR Engine1 raw:', JSON.stringify(ocrText2));
      console.log('OCR Engine1 solved:', solved2);
      if (solved2 && solved2.length >= 3) solvedCaptcha = solved2;
    }

    if (!solvedCaptcha || solvedCaptcha.length < 3) {
      console.log('FATAL: OCR completely failed to solve captcha');
      return;
    }

    console.log('');
    console.log('=== STEP 2: Attempting Login ===');
    const studentId = process.env.STUDENT_ID || 'demo_student';
    const password = process.env.STUDENT_PASSWORD || 'demo_password';
    const loginResult = await loginAndFetchSemesters(
      studentId,
      password,
      solvedCaptcha,
      session
    );
    console.log('Login success:', loginResult.success);
    console.log('Message:', loginResult.message);
    console.log('Needs captcha retry:', loginResult.needsCaptchaRetry);
    console.log('Academic years:', JSON.stringify(loginResult.academicYears));
    console.log('Semesters:', JSON.stringify(loginResult.semesters));

    if (loginResult.success && loginResult.academicYears.length > 0) {
      const year = loginResult.academicYears[0].value;
      const sem = loginResult.semesters[0].value;
      console.log('');
      console.log('=== STEP 3: Fetching Attendance ===');
      console.log('Using year:', year, 'sem:', sem);
      const attendanceResult = await fetchAttendanceData(
        loginResult.session,
        loginResult.csrfToken,
        year,
        sem
      );
      console.log('Success:', attendanceResult.success);
      console.log('Data length:', attendanceResult.data?.length);
      if (attendanceResult.data && attendanceResult.data.length > 0) {
        console.log('First item:', JSON.stringify(attendanceResult.data[0]));
        console.log('All keys:', Object.keys(attendanceResult.data[0]));
      } else {
        console.log('NO DATA RETURNED — attendance is empty');
      }
    }
  } catch (err: unknown) {
    console.error('DIAGNOSIS ERROR:', err);
  }
}
diagnose();
