// ==================== TRACKER STATE ====================
function getTrackerData() {
    try { return JSON.parse(localStorage.getItem('jobTracker') || '{}'); }
    catch (e) { return {}; }
}

function saveTrackerData(data) {
    localStorage.setItem('jobTracker', JSON.stringify(data));
}

// ==================== TRACKER UI ====================
function initTracker() {
    const trackerData = getTrackerData();
    const cards = document.querySelectorAll('.job-card');

    cards.forEach(function (card) {
        const jobId = parseInt(card.getAttribute('data-job-id'));
        if (!jobId) return;

        const saved = trackerData[jobId] || {};
        const currentStatus = saved.status || 'not-applied';
        const updatedDate = saved.updatedAt
            ? new Date(saved.updatedAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
            : '';

        const trackerRow = document.createElement('div');
        trackerRow.className = 'tracker-row';
        trackerRow.innerHTML =
            '<label>&#128203; Status:</label>' +
            '<select id="tracker-' + jobId + '" class="tracker-select status-' + currentStatus + '" onchange="updateTracker(' + jobId + ', this.value)">' +
            '<option value="not-applied"' + (currentStatus === 'not-applied' ? ' selected' : '') + '>Not Applied</option>' +
            '<option value="applied"' + (currentStatus === 'applied' ? ' selected' : '') + '>Applied</option>' +
            '<option value="shortlisted"' + (currentStatus === 'shortlisted' ? ' selected' : '') + '>Shortlisted</option>' +
            '<option value="interview"' + (currentStatus === 'interview' ? ' selected' : '') + '>Interview</option>' +
            '<option value="offer"' + (currentStatus === 'offer' ? ' selected' : '') + '>Offer</option>' +
            '<option value="rejected"' + (currentStatus === 'rejected' ? ' selected' : '') + '>Rejected</option>' +
            '</select>' +
            '<span class="tracker-date" id="tracker-date-' + jobId + '">' +
            (currentStatus !== 'not-applied' ? 'Updated: ' + updatedDate : '') +
            '</span>';

        card.appendChild(trackerRow);
    });

    updateSummaryStats();
}

function updateTracker(jobId, status) {
    const data = getTrackerData();
    data[jobId] = { status: status, updatedAt: new Date().toISOString() };
    saveTrackerData(data);

    const sel = document.getElementById('tracker-' + jobId);
    if (sel) { sel.className = 'tracker-select status-' + status; }

    const dateSpan = document.getElementById('tracker-date-' + jobId);
    if (dateSpan) {
        if (status === 'not-applied') { dateSpan.textContent = ''; }
        else {
            dateSpan.textContent = 'Updated: ' + new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
        }
    }
    updateSummaryStats();
}

function updateSummaryStats() {
    const data = getTrackerData();
    let applied = 0, interview = 0, offer = 0;
    Object.values(data).forEach(function (d) {
        if (d.status === 'applied' || d.status === 'shortlisted' || d.status === 'interview' || d.status === 'offer') applied++;
        if (d.status === 'interview') interview++;
        if (d.status === 'offer') offer++;
    });
    const el = document.getElementById('tracker-stats');
    if (el) {
        el.innerHTML = '<span class="stats-applied">' + applied + ' Applied</span> | ' +
            '<span class="stats-interview">' + interview + ' Interview</span> | ' +
            '<span class="stats-offer">' + offer + ' Offer</span>';
    }
}

// ==================== EXPORT & RESET ====================
function exportTracker() {
    const data = getTrackerData();
    const jobs = window.appState.jobs;
    let csv = 'Job #,Role,Company,Location,Status,Last Updated\n';
    Object.keys(data).forEach(function (num) {
        const job = jobs.find(j => j.id === parseInt(num));
        if (job && data[num].status !== 'not-applied') {
            csv += num + ',"' + job.title + '","' + job.company + '","' + job.location + '","' +
                data[num].status + '","' + new Date(data[num].updatedAt).toLocaleDateString('en-GB') + '"\n';
        }
    });
    downloadBlob(csv, 'Job_Application_Tracker_' + new Date().toISOString().slice(0, 10) + '.csv', 'text/csv');
}

function clearTracker() {
    if (confirm('Are you sure you want to reset all tracker data? This cannot be undone.')) {
        localStorage.removeItem('jobTracker');
        location.reload();
    }
}
