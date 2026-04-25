// ==================== FILTER INITIALIZATION ====================
function initFilters(jobs, config) {
    const container = document.getElementById('filters-container');
    if (!container) return;

    // Get unique values
    const countries = [...new Set(jobs.map(j => j.country))].sort();
    const matchRanges = [
        { value: 'all', label: 'All Matches' },
        { value: '90', label: '90%+' },
        { value: '85', label: '85%+' },
        { value: '80', label: '80%+' },
        { value: 'unscored', label: 'Unscored' }
    ];

    container.innerHTML =
        '<label>Filter:</label>' +
        // Country filter
        '<select id="filter-country" onchange="applyFilters()">' +
        '<option value="all">All Countries</option>' +
        countries.map(c => '<option value="' + c + '">' + c + '</option>').join('') +
        '</select>' +
        // Type filter
        '<select id="filter-type" onchange="applyFilters()">' +
        '<option value="all">All Roles</option>' +
        config.sections.map(s => '<option value="' + s.id + '">' + s.label.replace(/^[A-Z]\.\s*/, '') + '</option>').join('') +
        '</select>' +
        // Match filter
        '<select id="filter-match" onchange="applyFilters()">' +
        matchRanges.map(m => '<option value="' + m.value + '">' + m.label + '</option>').join('') +
        '</select>' +
        // Search
        '<input type="text" id="filter-search" placeholder="Search title, company..." oninput="applyFilters()" style="flex:1;min-width:180px">' +
        // Status filter
        '<select id="filter-status" onchange="applyFilters()">' +
        '<option value="all">All Status</option>' +
        '<option value="not-applied">Not Applied</option>' +
        '<option value="applied">Applied</option>' +
        '<option value="shortlisted">Shortlisted</option>' +
        '<option value="interview">Interview</option>' +
        '<option value="offer">Offer</option>' +
        '<option value="rejected">Rejected</option>' +
        '</select>';
}

// ==================== APPLY FILTERS ====================
function applyFilters() {
    const country = document.getElementById('filter-country').value;
    const type = document.getElementById('filter-type').value;
    const match = document.getElementById('filter-match').value;
    const search = document.getElementById('filter-search').value.toLowerCase().trim();
    const status = document.getElementById('filter-status').value;
    const trackerData = getTrackerData();

    const cards = document.querySelectorAll('.job-card');
    const visibleSections = new Set();

    cards.forEach(function (card) {
        const jobId = parseInt(card.getAttribute('data-job-id'));
        const jobCountry = card.getAttribute('data-country');
        const jobType = card.getAttribute('data-type');
        const jobMatch = parseInt(card.getAttribute('data-match')) || 0;
        const jobTitle = card.querySelector('.job-title').textContent.toLowerCase();
        const jobMeta = card.querySelector('.job-meta').textContent.toLowerCase();
        const jobStatus = (trackerData[jobId] && trackerData[jobId].status) || 'not-applied';

        let visible = true;

        if (country !== 'all' && jobCountry !== country) visible = false;
        if (type !== 'all' && jobType !== type) visible = false;
        if (match === 'unscored' && jobMatch > 0) visible = false;
        if (match !== 'all' && match !== 'unscored' && jobMatch < parseInt(match)) visible = false;
        if (search && !jobTitle.includes(search) && !jobMeta.includes(search)) visible = false;
        if (status !== 'all' && jobStatus !== status) visible = false;

        card.style.display = visible ? '' : 'none';
        if (visible) visibleSections.add(jobType);
    });

    // Show/hide section titles
    document.querySelectorAll('.section-title').forEach(function (title) {
        const sectionId = title.getAttribute('data-section');
        if (type !== 'all') {
            title.style.display = sectionId === type ? '' : 'none';
        } else {
            title.style.display = '';
        }
    });
}
