import {createCustomElement} from './helpers/create-custom-element.js';
import './tapered-rule.js';

fetch('static/files/statblock/src/templates/top-stats.html')
  .then(stream => stream.text())
  .then(htmlContent => {
    let contentNode =
      document.createRange().createContextualFragment(htmlContent);
    createCustomElement('top-stats', contentNode);
  });
