// Native dialog provides focus containment, Escape dismissal, and focus return.
const aboutDialog = document.getElementById('about-dialog');
document.getElementById('about-open').addEventListener('click', () => {
  aboutDialog.showModal();
  aboutDialog.scrollTop = 0;
  document.body.classList.add('dialog-open');
});
document.getElementById('about-close').addEventListener('click', () => aboutDialog.close());
aboutDialog.addEventListener('close', () => {
  document.body.classList.remove('dialog-open');
  document.getElementById('about-open').focus();
});
aboutDialog.addEventListener('click', event => {
  const rect = aboutDialog.getBoundingClientRect();
  if (event.target === aboutDialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) aboutDialog.close();
});
