/**
 * Adds logic to disable submission on the rating page if:
 *  - all checkboxes are unchecked
 *
 * Disables ratings if:
 *  - none of the above is checked
 *
 * Disables none of the above if:
 *  - any of the ratings are checked.
 */
document.addEventListener('DOMContentLoaded', () => {
  let form = document.querySelector('#rating');
  let submitButton = document.querySelector('#submit');
  let noneOfTheAboveBox = form.querySelector('input[name=none]');
  let ratingCheckboxes = form.querySelectorAll('input[name^=tag-]');

  enableCorrectControls();
  form.addEventListener('change', () => {
    enableCorrectControls()
  });

  function enableCorrectControls() {
    switch (stateOfTheForm()) {
      case 'disable-submit':
        submitButton.disabled = true;
        enableChoice(noneOfTheAboveBox);
        enableRatings();
        break;
      case 'disable-none-of-the-above':
        submitButton.disabled = false;
        disableChoice(noneOfTheAboveBox);
        enableRatings();
        break;

      case 'disable-ratings':
        submitButton.disabled = false;
        enableChoice(noneOfTheAboveBox);
        disableRatings();
        break;
    }
  }

  function stateOfTheForm() {
    let anyRatingChecked = false;
    for (let box of ratingCheckboxes) {
      anyRatingChecked ||= box.checked;
    }
    let noneOfTheAboveChecked = noneOfTheAboveBox.checked;

    if (anyRatingChecked && !noneOfTheAboveChecked) {
      return 'disable-none-of-the-above';
    } else if (noneOfTheAboveChecked && !anyRatingChecked) {
      return 'disable-ratings';
    } else {
      return 'disable-submit';
    }
  }

  function enableRatings() {
    for (let box of ratingCheckboxes) {
      enableChoice(box);
    }
  }

  function disableRatings() {
    for (let box of ratingCheckboxes) {
      disableChoice(box);
    }
  }

  function enableChoice(box) {
    box.disabled = false;
    box.closest('.choice').classList.remove('choice--disabled');
  }

  function disableChoice(box) {
    box.disabled = true;
    box.closest('.choice').classList.add('choice--disabled');
  }
});
