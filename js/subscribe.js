// Subscribe form handler — captures emails into Resend via /api/subscribe.
// Any <form data-resend-subscribe> on the page gets wired up.
//
// Expected markup (one of):
//   <form data-resend-subscribe>
//     <input type="email" name="email" required>
//     <button type="submit">Subscribe</button>
//     <p class="zn-subscribe-status" data-subscribe-status hidden></p>
//   </form>
//
// Status messages are written to .zn-subscribe-status (created on the fly
// if missing). The button text becomes "Subscribing…" then "✓ Subscribed"
// on success.

(function () {
  if (window.__resendSubscribeWired) return;
  window.__resendSubscribeWired = true;

  function wire(form) {
    if (form.dataset.resendWired) return;
    form.dataset.resendWired = '1';

    form.addEventListener('submit', async function (e) {
      e.preventDefault();

      const emailInput = form.querySelector('input[name="email"]');
      const button = form.querySelector('button[type="submit"]');
      let status = form.querySelector('[data-subscribe-status]');

      if (!emailInput || !button) return;
      const email = emailInput.value.trim();
      if (!email) return;

      // Ensure a status element exists.
      if (!status) {
        status = document.createElement('p');
        status.className = 'zn-subscribe-status';
        status.setAttribute('data-subscribe-status', '');
        status.hidden = true;
        form.appendChild(status);
      }

      const originalBtnText = button.textContent;
      button.disabled = true;
      button.textContent = 'Subscribing…';
      status.hidden = true;
      status.classList.remove('is-error');

      try {
        const resp = await fetch('/api/subscribe', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email }),
        });

        if (resp.ok) {
          // Redirect to the thanks page. Brief delay lets the button state
          // update so the click feels acknowledged before navigation.
          button.textContent = '✓ Subscribed';
          setTimeout(function () {
            window.location.href = '/subscribe/confirmed/';
          }, 250);
        } else {
          let msg = "Couldn't subscribe — try again?";
          try {
            const data = await resp.json();
            if (data && data.error === 'invalid email') {
              msg = 'That email looks off — double-check?';
            }
          } catch {}
          button.textContent = originalBtnText;
          button.disabled = false;
          status.textContent = msg;
          status.classList.add('is-error');
          status.hidden = false;
        }
      } catch (err) {
        button.textContent = originalBtnText;
        button.disabled = false;
        status.textContent = 'Network error — try again?';
        status.classList.add('is-error');
        status.hidden = false;
      }
    });
  }

  function wireAll() {
    document.querySelectorAll('form[data-resend-subscribe]').forEach(wire);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wireAll);
  } else {
    wireAll();
  }
})();
