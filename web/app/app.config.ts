// Nuxt UI theme mapping. Custom semantic trading colors (up/down/warning) are
// defined as Tailwind v4 design tokens in app/assets/css/main.css.
export default defineAppConfig({
  ui: {
    colors: {
      primary: 'teal',
      neutral: 'slate',
      success: 'emerald',
      warning: 'amber',
      error: 'rose',
      info: 'sky',
    },
    // Dense, professional defaults for a trading terminal.
    button: {
      defaultVariants: {
        size: 'sm',
      },
    },
    card: {
      slots: {
        root: 'rounded-lg',
      },
    },
  },
})
