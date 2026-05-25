/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../fit_sinc/web/templates/**/*.html",
    "../fit_sinc/web/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0f766e",
          dark: "#0d5c56",
          light: "#14b8a6",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
