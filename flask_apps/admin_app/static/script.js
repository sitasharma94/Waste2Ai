// Admin Dashboard helpers.
//  - [data-href]: makes a button navigate (e.g. "Add User" inside the search form).
//  - form[data-confirm]: asks for confirmation before submitting a state-changing action.

document.addEventListener('click', function (event) {
    var target = event.target.closest('[data-href]');
    if (target) {
        event.preventDefault();
        window.location.href = target.getAttribute('data-href');
    }
});

document.addEventListener('submit', function (event) {
    var message = event.target.getAttribute('data-confirm');
    if (message && !window.confirm(message)) {
        event.preventDefault();
    }
});
