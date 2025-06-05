local Plug = vim.fn['plug#']
local option = vim.opt
local global = vim.g
local option_local = vim.opt_local

global.mapleader = " "
require("config.lazy")


-- Plug("sainnhe/gruvbox-material")                                  -- colorscheme
-- Plug("osyo-manga/vim-over")                                       -- visual find and replace
-- Plug("junegunn/fzf")                                              -- findfiles
-- Plug("junegunn/fzf.vim")
-- Plug("preservim/nerdtree")                                        -- navigation
-- Plug("gu-fan/riv.vim")                                            -- rst
-- Plug("ntpeters/vim-better-whitespace")                            -- highlight trailing white space
-- Plug("bkad/CamelCaseMotion")                                      -- Camelcase Movement
-- Plug("vim-airline/vim-airline")
-- Plug("vim-airline/vim-airline-themes")                            -- statusbar
-- Plug("justinmk/vim-sneak")                                        -- Regex preview
-- Plug("christoomey/vim-tmux-navigator")                            -- tmux integration
-- Plug("neoclide/coc.nvim", { ['branch'] = 'release' })             -- autocomplete
-- Plug("pearofducks/ansible-vim")                                   -- ansible support
-- Plug("tpope/vim-surround")                                        -- Surround tools
-- Plug("tpope/vim-commentary")                                      -- Commenting
-- Plug("nvim-treesitter/nvim-treesitter", { ['do'] = ':TSUpdate' }) -- Parsers used by render-markdown
-- Plug("MeanderingProgrammer/render-markdown.nvim")                 -- Markdown preview in nvim
-- Plug("echasnovski/mini.icons", { branch = 'stable' })             -- Icons
--
-- vim.call('plug#end')


option.cursorline = true                                                       --Show current editor line
option.expandtab = true                                                        -- Convert tabs to spaces
option.gdefault = true                                                         -- add /g to replace by default
option.ignorecase = true                                                       -- ignore case when searching
option.modelines = 0                                                           -- Ignore vim setting in start of file
option.relativenumber = true                                                   -- Show relative numbers
option.scrolloff = 3                                                           -- When scrolling, keep this number of lines visible below
option.shiftwidth = 4                                                          -- number of spaces to use for autoindenting
option.showmatch = true                                                        -- option.show = true matching parenthesis
option.showmode = false                                                        -- Don't current mode
option.smartcase = true                                                        -- ignore case if search pattern is all lowercase,
option.tabstop = 4                                                             -- a tab is four spaces
option.undofile = true                                                         -- persistent undo
option.visualbell = true                                                       -- Dont beep, make it visual
option.wildignore = "*.swp,*.bak,*.pyc,*.class,tmp/**,dist/**,node_modules/**" -- wildmenu: ignore these extensions
option.shell =
"bash"                                                                         -- Required to let zsh know how to run things on command line
option.wildmode = "list:longest"
option.showbreak = "↪"

-- Wrapping
option.wrap = true
option.textwidth = 79
option.formatoptions = "qrn1"
option.colorcolumn = "85"

vim.api.nvim_create_autocmd("FocusLost", {
    pattern = "*",
    callback = function()
        vim.cmd(":wall")
    end,
})

vim.api.nvim_create_autocmd("BufRead", {
    pattern = "~/.mutt*",
    callback = function()
        option.tw = 72
    end,
})

vim.api.nvim_create_autocmd("BufWritePre", {
    pattern = "*.py",
    callback = function()
        vim.cmd("StripWhitespace")
        --        vim.fn.CocAction('runCommand', 'python.sortImports')
    end,
})

vim.api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, {
    pattern = "*.rst",
    callback = function()
        option.tw = 0
        option_local.filetype = "rst";
        option_local.wrap = false;
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "javascript",
    callback = function()
        option_local.shiftwidth = 2
        option_local.softtabstop = 2
        option_local.expandtab = true
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "typescript",
    callback = function()
        option_local.shiftwidth = 2
        option_local.softtabstop = 2
        option_local.expandtab = true
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "yaml",
    callback = function()
        option_local.shiftwidth = 2
        option_local.softtabstop = 2
        option_local.expandtab = true
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "tf",
    callback = function()
        option_local.shiftwidth = 2
        option_local.softtabstop = 2
        option_local.expandtab = true
    end,
})

-- colors
option.background = "dark"
global.gruvbox_material_background = "soft"
global.gruvbox_material_better_performance = true
-- colors:ansible
global.airline_theme = "gruvbox_material"
global.airline_powerline_fonts = 1
global.airline_solarized_bg = "light"


-- Window Resizing
vim.keymap.set("n", "<Left>", ":vertical resize +1<CR>")
vim.keymap.set("n", "<Right>", ":vertical resize -1<CR>")
vim.keymap.set("n", "<Up>", ":resize +1<CR>")
vim.keymap.set("n", "<Down>", ":resize -1<CR>")

-- Fuzzy search Config
vim.keymap.set("n", "<Leader>ff", ":Files<CR>")
vim.keymap.set("n", "<Leader>fb", ":Buffers<CR>")

-- Nerdtree config
global.NERDTreeIgnore = { ".pyc$" }
global.NERDTreeMapJumpNextSibling = ""
global.NERDTreeMapJumpPrevSibling = ""
vim.keymap.set("n", "<Leader>d", ":NERDTreeToogle<CR>")
vim.keymap.set("n", "<Leader>nt", ":NERDTreeFind<CR>")

-- Emmet Config
global.user_emmet_install_global = false

-- Coc
global.coc_global_extensions = { "coc-json", "coc-git", "@yaegassy/coc-ansible",
    "coc-docker", "coc-esbonio", "coc-eslint", "coc-highlight", "coc-html",
    "@yaegassy/coc-nginx", "coc-pyright", "coc-snippets", "coc-sql",
    "coc-tsserver", "coc-yaml", "coc-prettier", "coc-clangd",
    "coc-lua" }

local function register_mappings(mappings, default_options)
    for mode, mode_mappings in pairs(mappings) do
        for _, mapping in pairs(mode_mappings) do
            local options = #mapping == 3 and table.remove(mapping) or default_options
            local prefix, cmd = unpack(mapping)
            pcall(vim.api.nvim_set_keymap, mode, prefix, cmd, options)
        end
    end
end

function _G.check_back_space()
    local col = vim.fn.col('.') - 1
    if col == 0 or vim.fn.getline('.'):sub(col, col):match('%s') then
        return true
    else
        return false
    end
end

function _G.show_docs()
    local cw = vim.fn.expand('<cword>')
    if vim.fn.index({ 'vim', 'help' }, vim.bo.filetype) >= 0 then
        vim.cmd('h ' .. cw)
    elseif vim.api.nvim_eval('coc#rpc#ready()') then
        vim.fn.CocActionAsync('doHover')
    else
        vim.cmd('!' .. vim.o.keywordprg .. ' ' .. cw)
    end
end

local mappings = {
    i = { -- Insert mode
        { "<TAB>",     'pumvisible() ? "<C-N>" : v:lua.check_back_space() ? "<TAB>" : coc#refresh()', { expr = true } },
        { "<S-TAB>",   'pumvisible() ? "<C-P>" : "<C-H>"',                                            { expr = true } },
        { "<C-SPACE>", 'coc#refresh()',                                                               { expr = true } },
        { '<C-F>',     'coc#float#has_scroll() ? coc#float#scroll(1) : "<Right>"',                    { expr = true, silent = true, nowait = true } },
        { '<C-B>',     'coc#float#has_scroll() ? coc#float#scroll(0) : "<Left>"',                     { expr = true, silent = true, nowait = true } },
        --      {'<CR>',  'v:lua.MUtils.completion_confirm()', {expr = true, noremap = true}}
    },
    n = { -- Normal mode
        { "K",     '<CMD>lua _G.show_docs()<CR>',                            { silent = true } },
        { '[g',    '<Plug>(coc-diagnostic-prev)',                            { noremap = false } },
        { ']g',    '<Plug>(coc-diagnostic-next)',                            { noremap = false } },
        { 'gb',    '<Plug>(coc-cursors-word)',                               { noremap = false } },
        { 'gd',    '<Plug>(coc-definition)',                                 { noremap = false } },
        { 'gy',    '<Plug>(coc-type-definition)',                            { noremap = false } },
        { 'gi',    '<Plug>(coc-implementation)',                             { noremap = false } },
        { 'gr',    '<Plug>(coc-references)',                                 { noremap = false } },

        { '<C-F>', 'coc#float#has_scroll() ? coc#float#scroll(1) : "<C-F>"', { expr = true, silent = true, nowait = true } },
        { '<C-B>', 'coc#float#has_scroll() ? coc#float#scroll(0) : "<C-B>"', { expr = true, silent = true, nowait = true } },

    },
    o = {},
    t = { -- Terminal mode
    },
    v = { -- Visual/Select mode
    },
    x = { -- Visual mode
        { "<leader>a", '<CMD>lua _G.show_docs()<CR>', { silent = true } },
    },
    [""] = {
    },
}
register_mappings(mappings, { silent = true, noremap = true })

-- Ansible
global.coc_filetype_map = { ["yaml.ansible"] = "ansible" }

vim.cmd([[


autocmd CursorHold * silent call CocActionAsync('highlight')
set updatetime=300 "default 4000=4s, which may be slow
]])

require("render-markdown").setup({
    latex = { enabled = false, }, d
})

require('nvim-treesitter.configs').setup({
    highlight = { enable = true },
})

require("mini.icons").setup()
