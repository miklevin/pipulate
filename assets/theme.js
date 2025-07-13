/**
 * THEME SYSTEM
 * 
 * Handles theme preference loading, application, and management.
 * Provides sticky theme preference using localStorage.
 * 
 * This script runs immediately (IIFE) to prevent flash of wrong theme,
 * then provides comprehensive theme management functions.
 */

console.log('🎨 Theme system loading');

// IMMEDIATE THEME APPLICATION (prevents flash of wrong theme)
(function() {
    console.log('🎨 Initializing theme preferences');
    
    // Get theme from localStorage - this is the source of truth for stickiness
    let themeToApply = localStorage.getItem('theme_preference');
    
    if (!themeToApply || (themeToApply !== 'light' && themeToApply !== 'dark')) {
        // Default to dark mode for new users (sticky preference)
        themeToApply = 'dark';
        localStorage.setItem('theme_preference', themeToApply);
        console.log('🌙 No theme preference found - defaulting to dark mode');
    } else {
        console.log(`🎨 Applying saved theme: ${themeToApply}`);
    }
    
    document.documentElement.setAttribute('data-theme', themeToApply);
    console.log('✅ Theme applied successfully');
})();

// THEME MANAGEMENT FUNCTIONS

/**
 * Initialize theme management functionality.
 * Ensures switch state matches localStorage (sticky preference).
 * 
 * @param {string} serverTheme - The current theme from the server
 */
window.initializeThemeManagement = function(serverTheme) {
    console.log('🌙 Initializing theme management with server theme:', serverTheme);
    
    // localStorage is the source of truth for stickiness
    const currentTheme = localStorage.getItem('theme_preference') || 'dark';
    
    if (currentTheme !== serverTheme) {
        console.log('🌙 Theme mismatch - updating server to match localStorage:', currentTheme);
        // Update server to match localStorage
        fetch('/sync_theme', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'theme=' + currentTheme
        }).catch(error => {
            console.error('🌙 Failed to sync theme with server:', error);
        });
    }
    
    // Ensure DOM reflects localStorage
    document.documentElement.setAttribute('data-theme', currentTheme);
    console.log('🌙 Set DOM theme to:', currentTheme);
    
    // Update switch state to match localStorage
    const switchElement = document.querySelector('#theme-switch-container input[type="checkbox"]');
    if (switchElement) {
        switchElement.checked = (currentTheme === 'dark');
        console.log('🌙 Updated theme switch state to match theme:', currentTheme);
    } else {
        console.warn('🌙 Theme switch element not found');
    }
};

/**
 * Handle theme changes and update localStorage.
 * 
 * @param {string} newTheme - The new theme to apply
 */
window.handleThemeChange = function(newTheme) {
    console.log('🌙 Handling theme change to:', newTheme);
    
    // Update localStorage
    localStorage.setItem('theme_preference', newTheme);
    
    // Update DOM immediately
    document.documentElement.setAttribute('data-theme', newTheme);
    
    console.log('🌙 Theme changed to:', newTheme);
};

/**
 * Get the current theme preference.
 * 
 * @returns {string} The current theme ('dark' or 'light')
 */
window.getCurrentTheme = function() {
    return localStorage.getItem('theme_preference') || 'dark';
};

/**
 * Toggle between dark and light themes.
 */
window.toggleTheme = function() {
    const currentTheme = window.getCurrentTheme();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    window.handleThemeChange(newTheme);
    return newTheme;
};

/**
 * Apply theme directly to HTML element and store in localStorage.
 * Used by toggle_theme endpoint to externalize JavaScript.
 * 
 * @param {string} theme - The theme to apply ('light' or 'dark')
 */
window.applyThemeDirectly = function(theme) {
    console.log('🌙 Applying theme directly:', theme);
    
    // Apply theme to HTML element
    document.documentElement.setAttribute('data-theme', theme);
    
    // Store in localStorage for persistence across page loads
    localStorage.setItem('theme_preference', theme);
    
    console.log('🌙 Theme applied and stored:', theme);
};

console.log('✅ Theme system initialized'); 