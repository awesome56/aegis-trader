// ESLint flat config generated from the Nuxt module conventions.
// Run `npm run lint` after `nuxt prepare` has generated .nuxt/eslint.config.mjs.
import withNuxt from './.nuxt/eslint.config.mjs'
import prettier from 'eslint-config-prettier'

export default withNuxt(prettier, {
  rules: {
    'vue/multi-word-component-names': 'off',
  },
})
