return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      java = { "google-java-format" }, -- Formatting
      -- java = { "checkstyle" },      -- Linting (optional)
    },
    -- Custom formatter definition (if needed)
    formatters = {
      ["google-java-format"] = {
        command = "google-java-format",
        args = { "-" }, -- AOSP style (or omit for default)
        stdin = true,
      },
      -- ["checkstyle"] = { ... },    -- Define if using Checkstyle
    },
  },
}
