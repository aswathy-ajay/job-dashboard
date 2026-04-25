// ==================== CV STYLES ====================
const cvStylesHTML = 'body{font-family:Georgia,serif;max-width:800px;margin:0 auto;padding:40px;color:#222;line-height:1.5}h1{font-size:22pt;margin-bottom:2px;color:#1a3a5c;border-bottom:3px solid #1a3a5c;padding-bottom:8px}.cv-contact{font-size:10pt;color:#555;margin-bottom:20px}h2{font-size:13pt;border-bottom:2px solid #1a3a5c;padding-bottom:4px;margin:22px 0 10px;color:#1a3a5c;text-transform:uppercase;letter-spacing:1px}h3{font-size:11pt;margin:14px 0 4px;color:#333}p{font-size:10.5pt;margin:6px 0}ul{margin:4px 0 4px 20px}li{font-size:10.5pt;margin-bottom:4px}';

// ==================== HELPERS ====================
function getCVHTML(cvId) {
    const cv = window.appState.cvTemplates[cvId];
    if (!cv) { alert('CV template not found: ' + cvId); return null; }
    return cv.htmlContent;
}

function getJobById(jobId) {
    return window.appState.jobs.find(j => j.id === jobId);
}

function downloadBlob(content, fileName, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ==================== CV DOWNLOADS ====================
function downloadCVasPDF(cvId) {
    const content = getCVHTML(cvId);
    if (!content) return;
    const fullHTML = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>G Ajaykumar - CV</title><style>' + cvStylesHTML + '@media print{@page{margin:1.5cm}}</style></head><body>' + content + '</body></html>';
    const win = window.open('', '_blank');
    win.document.write(fullHTML);
    win.document.close();
    setTimeout(function () { win.print(); }, 500);
}

function downloadCVasDocx(cvId) {
    const content = getCVHTML(cvId);
    if (!content) return;
    const cv = window.appState.cvTemplates[cvId];
    const fileName = 'G_Ajaykumar_CV_' + (cv.displayName || cvId) + '.doc';
    const wordHTML = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">' +
        '<head><meta charset="UTF-8"><title>G Ajaykumar - CV</title>' +
        '<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->' +
        '<style>body{font-family:Georgia,serif;max-width:800px;margin:0 auto;padding:20px;color:#222;line-height:1.5}h1{font-size:18pt;margin-bottom:2px;color:#1a3a5c;border-bottom:2px solid #1a3a5c;padding-bottom:6px}.cv-contact{font-size:10pt;color:#555;margin-bottom:16px}h2{font-size:12pt;border-bottom:1.5px solid #1a3a5c;padding-bottom:3px;margin:18px 0 8px;color:#1a3a5c;text-transform:uppercase}h3{font-size:11pt;margin:12px 0 4px;color:#333}p{font-size:10.5pt;margin:4px 0}ul{margin:4px 0 4px 20px}li{font-size:10.5pt;margin-bottom:3px}</style></head><body>' + content + '</body></html>';
    downloadBlob(wordHTML, fileName, 'application/msword');
}

// ==================== COVER LETTER ====================
function generateCoverLetterHTML(jobId) {
    const job = getJobById(jobId);
    if (!job || !job.coverLetter || !job.coverLetter.body) return null;
    const config = window.appState.config;
    const person = config.person;
    const today = new Date();
    const dateStr = today.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
    const paragraphs = job.coverLetter.body.split('\n\n');
    let bodyHTML = '';
    paragraphs.forEach(function (p) { bodyHTML += '<p>' + p + '</p>'; });

    return '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">' +
        '<title>Cover Letter - ' + job.title + '</title>' +
        '<style>' +
        'body{font-family:Georgia,serif;max-width:700px;margin:0 auto;padding:50px 40px;color:#222;line-height:1.7;font-size:11.5pt}' +
        '.sender-info{text-align:left;margin-bottom:30px;font-size:10.5pt;color:#444}' +
        '.date{margin-bottom:20px}.recipient{margin-bottom:30px;font-size:10.5pt}' +
        '.salutation{margin-bottom:16px}p{margin-bottom:14px;text-align:justify}' +
        '.closing{margin-top:30px}.signature{margin-top:40px;font-weight:700}' +
        '.linkedin{font-size:10pt;color:#2d6a9f}' +
        '.print-btn{background:#8e44ad;color:#fff;padding:12px 28px;border:none;border-radius:8px;font-size:14px;cursor:pointer;margin-bottom:20px}' +
        '.print-btn:hover{background:#6c3483}@media print{.print-btn{display:none}body{padding:30px}@page{margin:2cm}}' +
        '</style></head><body>' +
        '<button class="print-btn" onclick="window.print()">Print / Save as PDF</button>' +
        '<div class="sender-info">' +
        person.fullName + ' (PMP, MCInstCES, Chartered Engineer)<br>' +
        person.contact.location + '<br>' +
        person.contact.phone + '<br>' +
        person.contact.email +
        '</div>' +
        '<div class="date">' + dateStr + '</div>' +
        '<div class="recipient">The Hiring Manager<br>' + job.company + '<br>' + job.location + '</div>' +
        '<div class="salutation">Dear Sir/Madam,</div>' +
        '<p>I am writing to express my interest in the <strong>' + job.title + '</strong> role in your esteemed organisation. With over 34 years of experience in project management, coupled with a Bachelor\'s degree in Civil Engineering and a PMP certification, I am confident in my ability to lead your project management team to success.</p>' +
        bodyHTML +
        '<p>I am enthusiastic about the opportunity to bring my experience in project management to your esteemed organisation and contribute to the continued success of your organization. I am confident that my skills and experience align perfectly with the needs of your team.</p>' +
        '<p>Thank you for considering my application. I look forward to the possibility of discussing how my experience and skills align with the needs of your team. I am available at your earliest convenience for an interview and can be reached at ' + person.contact.phone + ' or ' + person.contact.email + '.</p>' +
        '<div class="closing">Sincerely,</div>' +
        '<div class="signature">' + person.fullName + '</div>' +
        '<div class="linkedin">LinkedIn: ' + person.contact.linkedin + '</div>' +
        '</body></html>';
}

function downloadCoverLetter(jobId, format) {
    const html = generateCoverLetterHTML(jobId);
    if (!html) { alert('Cover letter data not found for job ' + jobId); return; }
    const job = getJobById(jobId);
    const safeName = job.title.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40);

    if (format === 'pdf') {
        const win = window.open('', '_blank');
        win.document.write(html);
        win.document.close();
        setTimeout(function () { win.print(); }, 500);
    } else if (format === 'docx') {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const bodyContent = doc.body.innerHTML;
        const wordHTML = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">' +
            '<head><meta charset="UTF-8"><title>Cover Letter</title>' +
            '<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->' +
            '<style>body{font-family:Georgia,serif;max-width:700px;margin:0 auto;padding:40px;color:#222;line-height:1.7;font-size:11.5pt}.sender-info{margin-bottom:30px;font-size:10.5pt;color:#444}.date{margin-bottom:20px}.recipient{margin-bottom:30px;font-size:10.5pt}p{margin-bottom:14px}.closing{margin-top:30px}.signature{margin-top:40px;font-weight:700}.linkedin{font-size:10pt;color:#2d6a9f}.print-btn{display:none}</style></head><body>' + bodyContent + '</body></html>';
        downloadBlob(wordHTML, 'G_Ajaykumar_CoverLetter_' + safeName + '.doc', 'application/msword');
    }
}
