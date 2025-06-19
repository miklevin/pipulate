/**
 * THEME INITIALIZATION
 * 
 * Handles theme preference loading and application on page load.
 * Provides sticky theme preference using localStorage.
 * 
 * This script runs immediately (IIFE) to prevent flash of wrong theme.
 */

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

// Global theme toggle function for UI controls
window.toggleTheme = function() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme_preference', newTheme);
    
    console.log(`🎨 Theme toggled to: ${newTheme}`);
    return newTheme;
}; 