return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      java = { "google-java-format" }, -- Formatting
      json = { "prettier" },
      html = { "prettier" },
      htmldjango = { "prettier" },
      -- java = { "checkstyle" },      -- Linting (optional)
    },
    -- Custom formatter definition (if needed)
    formatters = {
      ["markdownlint-cli2"] = {
        prepend_args = { "--config", vim.fn.stdpath("config") .. "/markdownlint-cli2.jsonc" },
      },
      ["google-java-format"] = {
        command = "google-java-format",
        args = { "-" }, -- AOSP style (or omit for default)
        stdin = true,
      },
      -- ["checkstyle"] = { ... },    -- Define if using Checkstyle
    },
  },
}
