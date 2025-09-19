// Trimmed JS: Removed interpolation & carousel logic no longer used after BusyBox redesign.
// Provides only navbar burger toggle for mobile.
$(document).ready(function() {
  $(".navbar-burger").on('click', function() {
    $(this).toggleClass("is-active");
    $("#mainNav").toggleClass("is-active");
  });
});
