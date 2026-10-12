/**
 * ComicCraft Interactive Workspace and Dynamic Progress Tracker
 */

document.addEventListener('DOMContentLoaded', () => {
  initCardSelectors();
  initProgressTracker();
  initRegenerationButtons();
});

// Card Selectors for Setting, Tone, Art Style
function initCardSelectors() {
  const groups = ['setting', 'tone', 'style'];
  
  groups.forEach(groupName => {
    const hiddenInput = document.getElementById(`input-${groupName}`);
    const cards = document.querySelectorAll(`.card-group-${groupName} .selectable-card`);
    
    if (cards.length > 0 && hiddenInput) {
      cards.forEach(card => {
        card.addEventListener('click', () => {
          cards.forEach(c => c.classList.remove('selected'));
          card.classList.add('selected');
          hiddenInput.value = card.getAttribute('data-value');
          
          // Live preview card update if applicable
          const previewElem = document.getElementById(`preview-${groupName}`);
          if (previewElem) {
            previewElem.textContent = card.getAttribute('data-value');
          }
        });
      });
    }
  });

  // Story idea live preview sync
  const promptInput = document.getElementById('story-prompt-input');
  const previewPrompt = document.getElementById('preview-story-text');
  if (promptInput && previewPrompt) {
    promptInput.addEventListener('input', (e) => {
      previewPrompt.textContent = e.target.value.trim() || 'Enter your story idea on the left to see the outline form...';
    });
  }
}

// Background Task Stage Progress Tracker
function initProgressTracker() {
  const statusContainer = document.getElementById('generation-status-box');
  if (!statusContainer) return;
  
  const comicId = statusContainer.getAttribute('data-comic-id');
  if (!comicId) return;

  const progressBar = document.getElementById('progress-bar-fill');
  const stageText = document.getElementById('current-stage-text');
  const percentText = document.getElementById('stage-percent-text');
  const stepsList = document.querySelectorAll('.progress-step-item');

  const checkInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/comics/${comicId}/status`);
      if (!res.ok) return;
      
      const data = await res.json();
      
      if (progressBar) progressBar.style.width = `${data.stage_percent}%`;
      if (stageText) stageText.textContent = data.current_stage;
      if (percentText) percentText.textContent = `${data.stage_percent}%`;

      // Update step highlights
      if (stepsList.length > 0) {
        stepsList.forEach((step, idx) => {
          const stepPercentThreshold = (idx + 1) * 20;
          if (data.stage_percent >= stepPercentThreshold) {
            step.classList.remove('active');
            step.classList.add('completed');
          } else if (data.stage_percent >= stepPercentThreshold - 20) {
            step.classList.add('active');
            step.classList.remove('completed');
          }
        });
      }

      // Check if finished
      if (data.status === 'completed') {
        clearInterval(checkInterval);
        setTimeout(() => {
          window.location.reload();
        }, 1200);
      } else if (data.status === 'failed') {
        clearInterval(checkInterval);
        if (stageText) {
          stageText.textContent = `Failed: ${data.error_message || 'An error occurred during generation'}`;
          stageText.style.color = '#FF3B30';
        }
      }
    } catch (err) {
      console.error('Error fetching comic status:', err);
    }
  }, 1500);
}

// Individual Panel Regeneration
function initRegenerationButtons() {
  const regenBtns = document.querySelectorAll('.btn-regen-panel');
  regenBtns.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const comicId = btn.getAttribute('data-comic-id');
      const panelId = btn.getAttribute('data-panel-id');
      
      if (!confirm('Regenerate illustration for this panel?')) return;
      
      btn.disabled = true;
      btn.textContent = 'Regenerating...';
      
      try {
        const res = await fetch(`/api/comics/${comicId}/panels/${panelId}/regenerate`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({})
        });
        
        if (res.ok) {
          const data = await res.json();
          const imgElem = document.getElementById(`panel-img-${panelId}`);
          if (imgElem && data.new_image_path) {
            // Append cache buster to force image reload
            imgElem.src = `${data.new_image_path}?t=${new Date().getTime()}`;
          }
          btn.textContent = 'Regenerated!';
          setTimeout(() => {
            btn.disabled = false;
            btn.textContent = 'Regenerate Panel';
          }, 2000);
        } else {
          alert('Failed to regenerate panel.');
          btn.disabled = false;
          btn.textContent = 'Regenerate Panel';
        }
      } catch (err) {
        alert('Error regenerating panel: ' + err.message);
        btn.disabled = false;
        btn.textContent = 'Regenerate Panel';
      }
    });
  });
}
