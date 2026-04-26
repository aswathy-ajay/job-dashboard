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

    // Also update the job's status in appState for consistency
    var job = window.appState.jobs.find(function (j) { return j.id === jobId; });
    if (job) { job.status = status; }

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
    updateUnappliedStat();
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

function updateUnappliedStat() {
    var jobs = window.appState.jobs;
    var trackerData = getTrackerData();
    var unapplied = 0;
    jobs.forEach(function (j) {
        var tracked = trackerData[j.id];
        var status = (tracked && tracked.status) ? tracked.status : (j.status || 'not-applied');
        if (status === 'not-applied') unapplied++;
    });
    var el = document.getElementById('stat-unapplied');
    if (el) el.textContent = unapplied;
}

// ==================== SYNC STATUS TO GITHUB ====================
async function syncStatusToGitHub() {
    var token = localStorage.getItem('githubPAT');
    if (!token) {
        token = prompt('Enter your GitHub Personal Access Token (fine-grained, contents:write permission) to sync status:');
        if (!token) return;
        localStorage.setItem('githubPAT', token);
    }

    var repo = window.appState.config.dashboard.repo;
    if (!repo) {
        repo = prompt('Enter your GitHub repo (e.g., aswathy-ajay/job-dashboard):');
        if (!repo) return;
    }

    var trackerData = getTrackerData();
    var statusPayload = JSON.stringify({ statuses: trackerData, lastSyncedAt: new Date().toISOString() }, null, 2);
    var contentBase64 = btoa(unescape(encodeURIComponent(statusPayload)));

    var apiUrl = 'https://api.github.com/repos/' + repo + '/contents/data/status.json';

    try {
        // Get current file SHA if it exists
        var sha = null;
        var existing = await fetch(apiUrl, { headers: { Authorization: 'token ' + token } });
        if (existing.ok) {
            var existingData = await existing.json();
            sha = existingData.sha;
        }

        var body = { message: 'Sync tracker status', content: contentBase64 };
        if (sha) body.sha = sha;

        var resp = await fetch(apiUrl, {
            method: 'PUT',
            headers: { Authorization: 'token ' + token, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (resp.ok) {
            alert('Status synced to GitHub successfully!');
        } else {
            var err = await resp.json();
            alert('Sync failed: ' + (err.message || resp.status));
            // If auth failed, clear the stored token
            if (resp.status === 401 || resp.status === 403) {
                localStorage.removeItem('githubPAT');
            }
        }
    } catch (e) {
        alert('Sync error: ' + e.message);
    }
}

function downloadStatusJSON() {
    var trackerData = getTrackerData();
    var payload = JSON.stringify({ statuses: trackerData, lastSyncedAt: new Date().toISOString() }, null, 2);
    downloadBlob(payload, 'status.json', 'application/json');
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
