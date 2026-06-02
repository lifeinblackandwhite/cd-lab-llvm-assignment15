document.addEventListener('DOMContentLoaded', () => {
    fetchData();
});

async function fetchData() {
    try {
        // Fetch the generated JSON from the outputs folder
        const response = await fetch('../outputs/secomd_results.json');
        if (!response.ok) throw new Error('Data not found');
        
        const data = await response.json();
        renderDashboard(data);
    } catch (error) {
        document.getElementById('tests-ul').innerHTML = `<li class="loading">❌ Error: Could not load data. Ensure you have run ./run.sh first and are serving via HTTP.</li>`;
        document.getElementById('repairs-ul').innerHTML = ``;
        console.error(error);
    }
}

function renderDashboard(data) {
    // 1. Populate Overview Stats
    const sum = data.summary;
    animateValue("stat-total", sum.total);
    animateValue("stat-passed", sum.passed);
    animateValue("stat-failed", sum.failed);
    animateValue("stat-sem-correct", sum.semantically_correct);
    animateValue("stat-sem-wrong", sum.semantically_wrong);

    // 2. Populate Test Cases List
    const testsUl = document.getElementById('tests-ul');
    testsUl.innerHTML = '';
    
    let delay = 0;
    for (const [name, result] of Object.entries(data.tests)) {
        const li = document.createElement('li');
        li.style.animationDelay = `${delay}s`;
        delay += 0.05;

        // Determine CSS classes for badges
        const statusClass = result.status === 'PASS' ? 'pass' : 'fail';
        const semanticClass = result.semantic === 'CORRECT' ? 'correct' : (result.semantic === 'WRONG' ? 'wrong' : 'unknown');

        li.innerHTML = `
            <span class="name">${name}</span>
            <span class="badge ${statusClass}">${result.status}</span>
            <span class="badge ${semanticClass}">${result.semantic || 'N/A'}</span>
            <span>${result.attempts}</span>
        `;
        testsUl.appendChild(li);
    }

    // 3. Populate Repair Loop List
    const repairsUl = document.getElementById('repairs-ul');
    repairsUl.innerHTML = '';
    
    delay = 0;
    for (const [errorType, result] of Object.entries(data.repair_results)) {
        const li = document.createElement('li');
        li.style.animationDelay = `${delay}s`;
        delay += 0.1;

        const statusClass = result.status === 'REPAIRED' ? 'repaired' : 'unrepaired';

        li.innerHTML = `
            <span class="name">${errorType}</span>
            <span class="badge ${statusClass}">${result.status}</span>
            <span>${result.attempts}</span>
        `;
        repairsUl.appendChild(li);
    }
}

// Helper to animate numbers counting up
function animateValue(id, end) {
    const obj = document.getElementById(id);
    if(end === 0) {
        obj.innerHTML = 0;
        return;
    }
    
    let start = 0;
    const duration = 1000;
    const increment = end / (duration / 16); // roughly 60fps
    
    function step() {
        start += increment;
        if (start >= end) {
            obj.innerHTML = end;
        } else {
            obj.innerHTML = Math.floor(start);
            requestAnimationFrame(step);
        }
    }
    requestAnimationFrame(step);
}
