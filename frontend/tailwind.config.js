/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../getsync/web/templates/**/*.html",
    "../getsync/web/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#4f46e5",
          dark: "#4338ca",
          light: "#6366f1",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
