// ==================== GLOBAL STATE ====================
window.appState = { config: null, jobs: [], cvTemplates: {} };

function escapeAttr(str) {
    if (!str) return '#';
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
}

// ==================== BOOT ====================
document.addEventListener('DOMContentLoaded', async function () {
    try {
        showLoading(true);
        const [config, jobsData, cvsData] = await Promise.all([
            fetchJSON('data/config.json'),
            fetchJSON('data/jobs.json'),
            fetchJSON('data/cvs.json')
        ]);

        window.appState.config = config;
        window.appState.jobs = jobsData.jobs;
        window.appState.cvTemplates = cvsData.cvTemplates;

        renderHeader(config);
        renderSummaryBar(jobsData.jobs, config);
        renderJobs(jobsData.jobs, config);
        initTracker();
        initFilters(jobsData.jobs, config);
        checkPauseWarning();
        showLoading(false);
    } catch (err) {
        showLoading(false);
        document.getElementById('jobs-container').innerHTML =
            '<div class="error">Failed to load dashboard data. Make sure you are serving this via HTTP (not file://). <br>Error: ' + err.message + '</div>';
        console.error(err);
    }
});

// ==================== DATA FETCHING ====================
async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error('Failed to fetch ' + url + ': ' + resp.status);
    return resp.json();
}

function showLoading(show) {
    const el = document.getElementById('loading');
    if (el) el.style.display = show ? 'block' : 'none';
}

// ==================== RENDER HEADER ====================
function renderHeader(config) {
    document.getElementById('header-title').textContent = config.dashboard.title;
    document.getElementById('header-credentials').textContent = config.person.credentials;
    document.getElementById('header-meta').textContent =
        'Updated: ' + config.dashboard.generatedDate + ' | Target: ' + config.dashboard.targetRegions;
}

// ==================== RENDER SUMMARY BAR ====================
function renderSummaryBar(jobs, config) {
    const scoredJobs = jobs.filter(j => j.matchPercent !== null);
    const countries = new Set(jobs.map(j => j.country));
    const types = new Set(jobs.map(j => j.type));
    const highestMatch = scoredJobs.length > 0 ? Math.max(...scoredJobs.map(j => j.matchPercent)) : 0;
    const unapplied = jobs.filter(j => !j.status || j.status === 'not-applied').length;

    document.getElementById('stat-total').textContent = jobs.length;
    document.getElementById('stat-highest').textContent = highestMatch + '%';
    document.getElementById('stat-countries').textContent = countries.size;
    document.getElementById('stat-types').textContent = types.size;
    document.getElementById('stat-unapplied').textContent = unapplied;
}

// ==================== PAUSE WARNING ====================
async function checkPauseWarning() {
    try {
        const flags = await fetchJSON('data/dashboard_flags.json');
        const warningEl = document.getElementById('pause-warning');
        if (flags.paused && warningEl) {
            warningEl.style.display = 'block';
            warningEl.innerHTML = '\u26A0\uFE0F <strong>Job hunting is PAUSED.</strong> You have ' +
                flags.unappliedCount + ' unapplied jobs (cap: 100). Please apply to more jobs before new ones are added.';
        }
    } catch (e) {
        // No flags file = not paused, ignore
    }
}

// ==================== RENDER JOBS ====================
function renderJobs(jobs, config) {
    const container = document.getElementById('jobs-container');
    container.innerHTML = '';

    // Group by section, sorted by matchPercent descending within each
    config.sections.forEach(function (section) {
        const sectionJobs = jobs.filter(j => j.type === section.id && j.matchPercent !== null)
            .sort(function (a, b) { return b.matchPercent - a.matchPercent; });
        if (sectionJobs.length === 0) return;

        // Section title
        const titleEl = document.createElement('div');
        titleEl.className = 'section-title';
        titleEl.setAttribute('data-section', section.id);
        titleEl.textContent = section.label + ' (' + sectionJobs.length + ' positions)';
        container.appendChild(titleEl);

        // Job cards
        sectionJobs.forEach(function (job) {
            container.appendChild(createJobCard(job));
        });
    });

    // Unscored jobs section (from scraper, not yet matched)
    const unscoredJobs = jobs.filter(j => j.matchPercent === null);
    if (unscoredJobs.length > 0) {
        const titleEl = document.createElement('div');
        titleEl.className = 'section-title';
        titleEl.setAttribute('data-section', 'unscored');
        titleEl.textContent = 'D. New Jobs (Pending Score) (' + unscoredJobs.length + ' positions)';
        container.appendChild(titleEl);
        unscoredJobs.forEach(function (job) {
            container.appendChild(createJobCard(job));
        });
    }
}

function createJobCard(job) {
    const card = document.createElement('div');
    card.className = 'job-card' + (job.matchPercent === null ? ' unscored' : '');
    card.setAttribute('data-country', job.country);
    card.setAttribute('data-type', job.type);
    card.setAttribute('data-match', job.matchPercent || 0);
    card.setAttribute('data-job-id', job.id);

    const matchClass = job.matchPercent === null ? 'match-none' :
        job.matchPercent >= 90 ? 'match-90' :
        job.matchPercent >= 85 ? 'match-85' : 'match-80';
    const matchText = job.matchPercent === null ? 'New' : job.matchPercent + '%';

    const tagsHTML = job.tags.map(t => '<span class="tag">' + t + '</span>').join('');
    const reqHTML = job.requirements.map(r => '<li>' + r + '</li>').join('');

    let matchAnalysisHTML = '';
    if (job.matchReasons && job.matchReasons.length > 0) {
        const reasonsHTML = job.matchReasons.map(r => '<li>' + r + '</li>').join('');
        matchAnalysisHTML = '<details><summary>View Match Analysis</summary>' +
            '<div class="match-reasons"><ul>' + reasonsHTML + '</ul></div></details>';
    }

    // Download buttons
    let downloadHTML = '';
    if (job.cvId) {
        downloadHTML += '<div class="download-group">' +
            '<div class="download-label">CV Downloads</div>' +
            '<a href="#" onclick="downloadCVasPDF(\'' + job.cvId + '\'); return false;" class="btn btn-cv-pdf">CV PDF</a>' +
            '<a href="#" onclick="downloadCVasDocx(\'' + job.cvId + '\'); return false;" class="btn btn-cv-docx">CV DOC</a>' +
            '</div>';
    }
    if (job.coverLetter && job.coverLetter.body) {
        downloadHTML += '<div class="download-group">' +
            '<div class="download-label">Cover Letter</div>' +
            '<a href="#" onclick="downloadCoverLetter(' + job.id + ', \'pdf\'); return false;" class="btn btn-cover">CL PDF</a>' +
            '<a href="#" onclick="downloadCoverLetter(' + job.id + ', \'docx\'); return false;" class="btn btn-cover" style="background:#6c3483">CL DOC</a>' +
            '</div>';
    }

    card.innerHTML = '<div class="job-header">' +
        '<div>' +
            '<div class="job-title">' + job.id + '. ' + job.title + '</div>' +
            '<div class="job-meta">' +
                '<span>&#127970; ' + job.company + '</span>' +
                '<span>&#128205; ' + job.location + '</span>' +
                '<span>&#128197; ' + job.datePosted + '</span>' +
                tagsHTML +
            '</div>' +
        '</div>' +
        '<div class="match-badge ' + matchClass + '">' + matchText + '</div>' +
        '</div>' +
        '<div class="job-description"><h4>Key Requirements:</h4><ul>' + reqHTML + '</ul></div>' +
        matchAnalysisHTML +
        '<div class="btn-group">' +
            '<a href="' + escapeAttr(job.applyUrl) + '" target="_blank" rel="noopener noreferrer" class="btn btn-apply">Apply &#8599;</a>' +
        '</div>' +
        '<div class="btn-group" style="margin-top:6px">' +
            downloadHTML +
        '</div>';

    return card;
}
