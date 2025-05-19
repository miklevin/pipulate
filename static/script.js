// 🌘 CSS Scope Inline (https://github.com/gnat/css-scope-inline)
window.cssScopeCount ??= 1 // Let extra copies share the scope count.
window.cssScope ??= new MutationObserver(mutations => { // Allow 1 observer.
	document?.body?.querySelectorAll('style:not([ready])').forEach(node => { // Faster than walking MutationObserver results when recieving subtree (DOM swap, htmx, ajax, jquery).
		var scope = 'me__'+(window.cssScopeCount++) // Ready. Make unique scope, example: .me__1234
		node.parentNode.classList.add(scope)
		node.textContent = node.textContent
		.replace(/(?:^|\.|(\s|[^a-zA-Z0-9\-\_]))(me|this|self)(?![a-zA-Z])/g, '$1.'+scope) // Can use: me this self
		.replace(/((@keyframes|animation:|animation-name:)[^{};]*)\.me__/g, '$1me__') // Optional. Removes need to escape names, ex: "\.me"
		.replace(/(?:@media)\s(xs-|sm-|md-|lg-|xl-|sm|md|lg|xl|xx)/g, // Optional. Responsive design. Mobile First (above breakpoint): 🟢 None sm md lg xl xx 🏁  Desktop First (below breakpoint): 🏁 xs- sm- md- lg- xl- None 🟢 *- matches must be first!
			(match, part1) => { return '@media '+({'sm':'(min-width: 640px)','md':'(min-width: 768px)', 'lg':'(min-width: 1024px)', 'xl':'(min-width: 1280px)', 'xx':'(min-width: 1536px)', 'xs-':'(max-width: 639px)', 'sm-':'(max-width: 767px)', 'md-':'(max-width: 1023px)', 'lg-':'(max-width: 1279px)', 'xl-':'(max-width: 1535px)'}[part1]) }
		)
		node.setAttribute('ready', '')
	})
}).observe(document.documentElement, {childList: true, subtree: true})

document.addEventListener('DOMContentLoaded', function() {
    if (window.pipulateScriptInitialized) {
        return; // Avoid multiple initializations if script is re-run via HTMX swap of body
    }
    window.pipulateScriptInitialized = true;

    console.log('Pipulate global scripts initialized.');

    // Debounce function to prevent multiple rapid scroll attempts
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function doScrollToBottom(scrollableElement) {
        if (!scrollableElement) {
            console.warn('No scrollable element provided to doScrollToBottom');
            return;
        }

        // Force a reflow to ensure scrollHeight is accurate
        scrollableElement.style.display = 'none';
        scrollableElement.offsetHeight; // Force reflow
        scrollableElement.style.display = '';

        const scrollHeight = scrollableElement.scrollHeight;
        const clientHeight = scrollableElement.clientHeight;
        const maxScroll = scrollHeight - clientHeight;

        console.log('Scrolling element:', {
            element: scrollableElement,
            scrollHeight,
            clientHeight,
            maxScroll,
            currentScroll: scrollableElement.scrollTop
        });

        // Use requestAnimationFrame for smoother scrolling
        requestAnimationFrame(() => {
            scrollableElement.scrollTo({
                top: maxScroll,
                behavior: 'smooth'
            });
        });
    }

    // Debounced version of doScrollToBottom
    const debouncedScroll = debounce(doScrollToBottom, 100);

    function findScrollablePanel() {
        // Try multiple selectors in order of preference
        const selectors = [
            '.main-grid > div:first-child',  // Primary selector
            '#grid-left-content',            // Alternative 1
            '.main-grid > div:first-of-type', // Alternative 2
            '.main-grid > div'               // Fallback
        ];

        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) {
                console.log('Found scrollable panel using selector:', selector);
                return element;
            }
        }

        console.warn('Could not find scrollable panel with any selector');
        return null;
    }

    // Listen for the custom event triggered by server via HX-Trigger-After-Settle
    document.body.addEventListener('scrollToLeftPanelBottom', function(event) {
        console.log('scrollToLeftPanelBottom event received:', event.detail);
        const leftPanel = findScrollablePanel();
        if (leftPanel) {
            debouncedScroll(leftPanel);
        }
    });

    // General listener for other hx_trigger="load" scenarios
    document.body.addEventListener('htmx:afterSettle', function(event) {
        const targetElement = event.detail.target;
        const requestConfig = event.detail.requestConfig;

        console.log('htmx:afterSettle event:', {
            targetId: targetElement.id,
            trigger: requestConfig?.trigger
        });

        // Check if the target is a step div or workflow container
        const isWorkflowContentLoad = targetElement.id && (
            targetElement.id.startsWith('step_') || 
            targetElement.id.endsWith('-container') ||
            targetElement.closest('.main-grid > div:first-child') // Also check if target is inside left panel
        );
        
        // Check if the original trigger for the HTMX request included 'load'
        const wasLoadTriggered = requestConfig && 
            requestConfig.trigger && 
            String(requestConfig.trigger).includes('load');

        if (isWorkflowContentLoad && wasLoadTriggered) {
            const leftPanel = findScrollablePanel();
            if (leftPanel) {
                console.log('Triggering scroll for workflow content load');
                debouncedScroll(leftPanel);
            }
        }
    });

    // Additional listener for content changes
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                const leftPanel = findScrollablePanel();
                if (leftPanel && leftPanel.contains(mutation.target)) {
                    console.log('Content changed in left panel, triggering scroll');
                    debouncedScroll(leftPanel);
                }
            }
        }
    });

    // Start observing the document with the configured parameters
    observer.observe(document.body, { 
        childList: true, 
        subtree: true 
    });
});