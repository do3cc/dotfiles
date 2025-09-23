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

      -- Empfohlen: keine args überschreiben, damit --stdin/--stdin-filepath erhalten bleiben
      -- markdownlint-cli2 findet die ~/.markdownlint-cli2.jsonc selbst beim Aufsteigen im Verzeichnisbaum.
      return opts
    end,
  },
}
