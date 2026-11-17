const DEMO_LISTINGS = [
  {"id":"1","title":"ASUCI General Club Fair","categories":["Clubs","Events"],"description":"Explore 100+ student organizations, grab free swag, and sign up for clubs that match your interests.","datetime":"Oct 29, 2025, 11:00 AM","location":"Ring Road, Main Campus","contact":"https://asuci.uci.edu/clubfair","source":"Club Website"},
  {"id":"2","title":"Part-Time Barista — Anteatery Café","categories":["Jobs"],"description":"On-campus café hiring part-time baristas. Flexible shifts, work-study eligible, training provided.","datetime":null,"location":"Anteatery, Student Center","contact":"https://jobs.uci.edu/listing/4821","source":"Career Center"},
  {"id":"3","title":"FRESH Basic Needs Hub — Free Groceries","categories":["Basic Needs"],"description":"Weekly grocery distribution for students facing food insecurity. No application needed, just bring your student ID.","datetime":"Every Tuesday, 10:00 AM - 2:00 PM","location":"FRESH Basic Needs Hub, G319 Student Center","contact":"fresh@uci.edu","source":"Canvas"},
  {"id":"4","title":"Subleaser Needed — Studio Near Campus","categories":["Housing"],"description":"Winter quarter sublease available, 5 min walk to campus, furnished studio, utilities included.","datetime":null,"location":"Camino Del Sol Apartments","contact":"subleasestudent@gmail.com","source":"Instagram"},
  {"id":"5","title":"Fall Career & Internship Fair","categories":["Career Fairs","Jobs"],"description":"Meet recruiters from 80+ companies hiring for internships and full-time roles across all majors.","datetime":"Nov 5, 2025, 10:00 AM - 3:00 PM","location":"Bren Events Center","contact":"https://career.uci.edu/fall-fair","source":"Career Center"},
  {"id":"6","title":"Mindfulness & Stress Relief Workshop","categories":["Health/Wellness"],"description":"Guided meditation and breathing exercises to help manage midterm stress. Open to all students.","datetime":"Oct 31, 2025, 4:00 PM","location":"Student Health Center, Room 201","contact":"wellness@uci.edu","source":"Student Health Center"},
  {"id":"7","title":"Computer Science Club Weekly Meeting","categories":["Clubs"],"description":"Weekly meetup for CS students: coding challenges, project showcases, and guest speaker talks.","datetime":"Every Wednesday, 6:00 PM","location":"DBH 1300","contact":"https://csclub.ics.uci.edu","source":"Club Website"},
  {"id":"8","title":"Campus Food Pantry Volunteer Opportunity","categories":["Basic Needs","Jobs"],"description":"Volunteer hours available for students who want to help stock and distribute food at the pantry.","datetime":null,"location":"FRESH Basic Needs Hub","contact":"fresh-volunteer@uci.edu","source":"Canvas"},
  {"id":"9","title":"Roommate Wanted — 2BR Apartment","categories":["Housing"],"description":"Looking for a clean, quiet roommate to share a 2-bedroom apartment starting Winter quarter. $900/month.","datetime":null,"location":"University Hills","contact":"roommatewanted@uci.edu","source":"Instagram"},
  {"id":"10","title":"Free Flu Shot Clinic","categories":["Health/Wellness","Events"],"description":"Free flu vaccinations for all students with valid student ID. Walk-ins welcome, no appointment needed.","datetime":"Nov 3, 2025, 9:00 AM - 1:00 PM","location":"Student Health Center Lobby","contact":"https://shc.uci.edu/flu","source":"Student Health Center"},
  {"id":"11","title":"Women in STEM Networking Night","categories":["Clubs","Career Fairs"],"description":"Connect with alumnae and industry professionals in STEM fields over dinner and casual networking.","datetime":"Nov 7, 2025, 6:00 PM","location":"Calit2 Auditorium","contact":"https://wistem.uci.edu/networking","source":"Club Website"},
  {"id":"12","title":"Resident Assistant (RA) Hiring","categories":["Jobs","Housing"],"description":"Housing office hiring RAs for next academic year. Free housing + stipend included. Applications due soon.","datetime":"Applications due Dec 1, 2025","location":"Housing Administration Office","contact":"https://housing.uci.edu/ra-jobs","source":"Canvas"},
  {"id":"13","title":"Late Night Study Jam & Free Snacks","categories":["Events","Basic Needs"],"description":"Finals prep event with free coffee, snacks, and quiet study space open until 2 AM.","datetime":"Dec 8, 2025, 8:00 PM - 2:00 AM","location":"Langson Library","contact":"https://library.uci.edu/latenight","source":"Instagram"},
  {"id":"14","title":"Peer Tutoring Program Sign-Up","categories":["Basic Needs","Clubs"],"description":"Free peer tutoring for math, chemistry, and physics courses. Sign up for weekly sessions.","datetime":null,"location":"Learning & Academic Resource Center","contact":"https://larc.sa.uci.edu","source":"Canvas"},
  {"id":"15","title":"Tech Company Info Session — DataCore Inc.","categories":["Career Fairs","Jobs"],"description":"Info session with Q&A about internship and new-grad software engineering roles. Pizza provided.","datetime":"Nov 12, 2025, 5:30 PM","location":"Engineering Hall 2430","contact":"https://career.uci.edu/datacore-infosession","source":"Career Center"},
  {"id":"16","title":"Yoga on the Lawn","categories":["Health/Wellness","Events"],"description":"Free weekly outdoor yoga session for all skill levels. Mats provided, just bring water.","datetime":"Every Friday, 3:00 PM","location":"Aldrich Park","contact":"wellness@uci.edu","source":"Instagram"},
  {"id":"17","title":"Emergency Housing Assistance Program","categories":["Housing","Basic Needs"],"description":"Short-term emergency housing support for students facing unexpected housing insecurity.","datetime":null,"location":"Dean of Students Office","contact":"deanofstudents@uci.edu","source":"Canvas"},
  {"id":"18","title":"Anteater Entrepreneurship Club Pitch Night","categories":["Clubs","Events"],"description":"Student founders pitch their startups to peers and local investors. Open to all majors, free admission.","datetime":"Nov 14, 2025, 7:00 PM","location":"The Cove, Student Center","contact":"https://aec.uci.edu/pitchnight","source":"Club Website"}
];

let UCI_EVENTS = [];
let LISTINGS = [];
let feedState = 'loading';
const activeCategories = new Set(['Events']);
const eventPeriod = document.getElementById('eventPeriod');
const showDemos = document.getElementById('showDemos');
const eventCategoryFilter = document.getElementById('eventCategoryFilter');
showDemos.addEventListener('change', () => {
  if (!showDemos.checked) {
    activeCategories.clear();
    activeCategories.add('Events');
  }
  render();
});
eventCategoryFilter.addEventListener('change', render);
eventPeriod.addEventListener('change', render);

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
}

function safeContact(value) {
  if (isEmail(value)) return `mailto:${value}`;
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : '';
  } catch { return ''; }
}

function eventDate(value, dateOnly = false) {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Los_Angeles', dateStyle: 'medium', ...(dateOnly ? {} : {timeStyle: 'short'})
  }).format(new Date(value));
}

function uniqueLabels(values) {
  const seen = new Set();
  return values.filter(value => typeof value === 'string').map(value => value.trim()).filter(value => {
    const key = value.toLowerCase();
    if (!value || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function updateEventCategoryFilter() {
  const selected = eventCategoryFilter.value;
  const counts = new Map();
  UCI_EVENTS.forEach(item => item.sourceCategories.forEach(category => counts.set(category, (counts.get(category) || 0) + 1)));
  eventCategoryFilter.innerHTML = '<option value="">All event categories</option>' +
    [...counts].sort(([a], [b]) => a.localeCompare(b)).map(([category, count]) =>
      `<option value="${escapeHtml(category)}">${escapeHtml(category)} (${count})</option>`).join('');
  eventCategoryFilter.value = counts.has(selected) ? selected : '';
}

function isPastEvent(item) {
  return Boolean(item.start && new Date(item.end || item.start).getTime() < Date.now());
}
let searchText = "";

const searchInput = document.getElementById('searchInput');
const categoryFilters = document.getElementById('categoryFilters');
const resultsInfo = document.getElementById('resultsInfo');
const cardGrid = document.getElementById('cardGrid');
const emptyState = document.getElementById('emptyState');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');

function isEmail(str) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(str);
}

function getFilteredListings() {
  return LISTINGS.filter(item => {
    const text = [item.title, item.description, item.organizer, item.location, ...(item.tags || [])].join(' ').toLowerCase();
    const matchesSearch = text.includes(searchText.toLowerCase());
    const matchesCategory = activeCategories.size === 0 ||
      item.categories.some(cat => activeCategories.has(cat));
    const matchesPeriod = !item.isEvent || eventPeriod.value === 'all' ||
      (eventPeriod.value === 'undated' ? !item.start : item.start &&
        (eventPeriod.value === 'past' ? isPastEvent(item) : !isPastEvent(item)));
    const matchesEventCategory = !eventCategoryFilter.value ||
      (item.isEvent && item.sourceCategories.includes(eventCategoryFilter.value));
    return matchesSearch && matchesCategory && matchesPeriod && matchesEventCategory;
  }).sort((a, b) => {
    if (!a.isEvent || !b.isEvent) return Number(Boolean(b.isEvent)) - Number(Boolean(a.isEvent));
    if (isPastEvent(a) !== isPastEvent(b)) return Number(isPastEvent(a)) - Number(isPastEvent(b));
    if (!a.start || !b.start) return Number(Boolean(b.start)) - Number(Boolean(a.start));
    return isPastEvent(a) ? new Date(b.start) - new Date(a.start) : new Date(a.start) - new Date(b.start);
  });
}

function renderCards(listings) {
  resultsInfo.textContent = `Showing ${listings.length} of ${LISTINGS.length} loaded listings`;

  if (listings.length === 0) {
    cardGrid.hidden = true;
    emptyState.hidden = false;
    cardGrid.innerHTML = '';
    return;
  }

  cardGrid.hidden = false;
  emptyState.hidden = true;

  cardGrid.innerHTML = listings.map((item, idx) => {
    const tagsHtml = (item.isEvent ? item.displayTags : item.categories).map((cat, i) => {
      const cls = item.isEvent ? (item.sourceCategories.includes(cat) ? 'blue-bg' : 'yellow-bg') : (i % 2 === 0 ? 'blue-bg' : 'yellow-bg');
      return `<span class="tag ${cls}">${escapeHtml(cat)}</span>`;
    }).join('');

    const dateLabel = item.isEvent && item.start
      ? `${eventDate(item.start, item.allDay)}${item.end && (!item.allDay || eventDate(item.end, true) !== eventDate(item.start, true)) ? ' – ' + eventDate(item.end, item.allDay) : ''}${item.allDay ? ' (all day)' : ' PT'}`
      : item.datetime;
    const datetimeRow = dateLabel
      ? `<div class="meta-row"><strong>When:</strong> ${escapeHtml(dateLabel)}</div>`
      : '';

    const contactHref = safeContact(item.contact);
    const contactLabel = item.isEvent ? (item.source === 'ZotSpot' ? 'View on ZotSpot ↗' : 'View official event ↗') : isEmail(item.contact) ? 'Email' : 'Visit Link';

    return `
      <div class="card">
        <h3>${escapeHtml(item.title)}</h3>
        <div class="tags">${tagsHtml}</div>
        <p class="desc">${escapeHtml(item.description)}</p>
        ${item.isEvent ? `<div class="meta-row"><strong>Organizer:</strong> ${escapeHtml(item.organizer)}</div><div class="meta-row">${!item.start ? 'Date to be confirmed' : isPastEvent(item) ? 'Past event' : 'Upcoming / ongoing'}${item.cost ? ' · ' + escapeHtml(item.cost) : ''}</div>` : '<div class="meta-row">Demo listing</div>'}
        ${datetimeRow}
        <div class="meta-row"><strong>Where:</strong> ${escapeHtml(item.location)}</div>
        ${contactHref ? `<a class="contact-link" href="${escapeHtml(contactHref)}" target="_blank" rel="noopener noreferrer">${contactLabel}</a>` : '<p class="meta-row">Official link not provided</p>'}
        <div class="via-source">via ${escapeHtml(item.source)}</div>
      </div>
    `;
  }).join('');
}

function render() {
  if (feedState !== 'ready') {
    cardGrid.hidden = true;
    emptyState.hidden = true;
    resultsInfo.textContent = feedState === 'loading' ? 'Loading UCI events…' : 'Event feed unavailable';
    return;
  }
  updateFilterButtonStates();
  LISTINGS = showDemos.checked ? [...UCI_EVENTS, ...DEMO_LISTINGS] : UCI_EVENTS;
  const filtered = getFilteredListings();
  renderCards(filtered);
}

searchInput.addEventListener('input', (e) => {
  searchText = e.target.value;
  render();
});

categoryFilters.addEventListener('click', (e) => {
  const btn = e.target.closest('.filter-btn');
  if (!btn) return;

  const category = btn.dataset.category;

  if (category === 'All') {
    activeCategories.clear();
  } else {
    if (activeCategories.has(category)) {
      activeCategories.delete(category);
    } else {
      activeCategories.add(category);
    }
  }

  updateFilterButtonStates();
  render();
});

function updateFilterButtonStates() {
  const buttons = categoryFilters.querySelectorAll('.filter-btn');
  buttons.forEach(btn => {
    const cat = btn.dataset.category;
    btn.hidden = !['All', 'Events'].includes(cat) && !showDemos.checked;
    if (cat === 'All') {
      btn.classList.toggle('active', activeCategories.size === 0);
      btn.setAttribute('aria-pressed', String(activeCategories.size === 0));
    } else {
      btn.classList.toggle('active', activeCategories.has(cat));
      btn.setAttribute('aria-pressed', String(activeCategories.has(cat)));
    }
  });
}

clearFiltersBtn.addEventListener('click', () => {
  searchText = '';
  searchInput.value = '';
  activeCategories.clear();
  eventPeriod.value = 'all';
  eventCategoryFilter.value = '';
  updateFilterButtonStates();
  render();
});

function normalizeFeed(rows) {
  if (!Array.isArray(rows)) throw new Error('The event feed must contain a JSON array.');
  const seen = new Set();
  return rows.map(row => {
    if (!row || typeof row !== 'object' || !row.id || typeof row.title !== 'string' || !row.title.trim()) {
      throw new Error('An event is missing its id or title.');
    }
    for (const field of ['start_datetime', 'end_datetime']) {
      const value = row[field];
      if (value != null && (typeof value !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value)))) {
        throw new Error('Event dates need timezone offsets. Run scripts/sync_events.py to export the crawler JSON.');
      }
    }
    if (row.end_datetime && (!row.start_datetime || Date.parse(row.end_datetime) < Date.parse(row.start_datetime))) {
      throw new Error('An event has an invalid date range.');
    }
    const source = typeof row.source === 'string' ? row.source : 'unknown';
    const sourceCategories = uniqueLabels(Array.isArray(row.categories) ? row.categories : []);
    const topics = uniqueLabels(Array.isArray(row.tags) ? row.tags : []);
    const displayTags = uniqueLabels([...sourceCategories, ...topics]);
    return {
      id: `${source}:${row.id}`, title: row.title,
      description: typeof row.description === 'string' ? row.description : '',
      start: row.start_datetime || null, end: row.end_datetime || null,
      categories: ['Events', ...sourceCategories], sourceCategories,
      displayTags: displayTags.length ? displayTags : ['Event'], tags: displayTags, allDay: row.all_day === true,
      location: row.location || 'Location not provided', organizer: row.organizer_name || 'Organizer not provided',
      contact: safeContact(row.rsvp_url || '') || safeContact(row.source_url || ''),
      source: source === 'zotspot' ? 'ZotSpot' : source, cost: row.cost || '',
      lastUpdated: typeof row.last_updated === 'string' ? row.last_updated : '', isEvent: true
    };
  }).filter(item => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}

async function loadEvents() {
  feedState = 'loading';
  document.getElementById('feedError').hidden = true;
  document.getElementById('snapshotNote').textContent = '';
  render();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch('./data/output/unified_events.json', {cache: 'no-cache', signal: controller.signal});
    if (!response.ok) throw new Error(`The event file could not be loaded (HTTP ${response.status}).`);
    UCI_EVENTS = normalizeFeed(await response.json());
    updateEventCategoryFilter();
    feedState = 'ready';
    const dates = UCI_EVENTS.map(item => item.lastUpdated.slice(0, 10)).filter(value => /^\d{4}-\d{2}-\d{2}$/.test(value)).sort();
    const updated = dates.length ? ` Latest record update: ${dates[dates.length - 1]}.` : '';
    document.getElementById('snapshotNote').textContent =
      `${UCI_EVENTS.length} events loaded from the saved event feed.${updated} Times shown in Pacific Time. Refreshing the page reads the latest published JSON; check the official source for current details.`;
  } catch (error) {
    feedState = 'error';
    UCI_EVENTS = [];
    document.getElementById('feedError').hidden = false;
    document.getElementById('feedErrorMessage').textContent = location.protocol === 'file:'
      ? 'To load the JSON event file, open this website through a web server. See the README for local startup instructions.'
      : `Unable to load UCI events. ${error.name === 'AbortError' ? 'The request timed out.' : error.message}`;
  } finally {
    clearTimeout(timeout);
    render();
  }
}

document.getElementById('retryFeed').addEventListener('click', loadEvents);
updateFilterButtonStates();
loadEvents();
