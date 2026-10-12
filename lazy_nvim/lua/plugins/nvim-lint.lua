return {
  {
    "mfussenegger/nvim-lint",
    event = { "BufReadPost", "BufNewFile" },
    opts = function(_, opts)
      opts = opts or {}
      opts.linters_by_ft = opts.linters_by_ft or {}

      -- Ganz wichtig: markdown -> markdownlint-cli2
      opts.linters_by_ft.markdown = { "markdownlint-cli2" }
      opts.linters_by_ft["markdown.mdx"] = { "markdownlint-cli2" }

      -- Global config (MD013 off) via --config, which overrides any project config.
      -- Keep "-" so the buffer is still read from stdin.
      local config = vim.fn.stdpath("config") .. "/markdownlint-cli2.jsonc"
      require("lint").linters["markdownlint-cli2"].args = { "--config", config, "-" }

      return opts
    end,
  },
}
