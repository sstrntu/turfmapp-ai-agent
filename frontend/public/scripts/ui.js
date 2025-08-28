'use strict';

/**
 * UI utilities (globals under window.UI)
 */
window.UI = window.UI || {};

/**
 * Position a floating popover element relative to a toggle button.
 * Uses fixed positioning to avoid clipping in scrollable containers.
 *
 * @param {HTMLElement} toggle - The anchor element that triggers the popover
 * @param {HTMLElement} pop - The popover element to position
 * @param {number} spacing - Gap in pixels between toggle and popover
 */
window.UI.positionPopover = function positionPopover(toggle, pop, spacing) {
    if (!toggle || !pop) return;
    const gap = typeof spacing === 'number' ? spacing : 8;

    // Prepare for measurement
    const prevDisplay = pop.style.display;
    const prevVisibility = pop.style.visibility;
    const prevPosition = pop.style.position;
    pop.style.position = 'fixed';
    pop.style.visibility = 'hidden';
    pop.style.display = 'block';

    const rect = toggle.getBoundingClientRect();
    let left = rect.left;
    let top = rect.top - pop.offsetHeight - gap; // place above by default

    // If off top, place below
    if (top < 8) top = rect.bottom + gap;

    // Constrain horizontally within viewport
    const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    const maxLeft = vw - pop.offsetWidth - 8;
    if (left > maxLeft) left = Math.max(8, maxLeft);
    if (left < 8) left = 8;

    pop.style.left = left + 'px';
    pop.style.top = top + 'px';

    // Restore
    pop.style.visibility = prevVisibility || 'visible';
    pop.style.display = prevDisplay || 'block';
    pop.style.position = prevPosition || 'fixed';
};


