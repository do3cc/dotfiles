set nocompatible
filetype off
execute pathogen#infect()
filetype plugin indent on


set modelines=0

set nowrap        " don't wrap lines
set tabstop=4     " a tab is four spaces
"set backspace=indent,eol,start
                  " allow backspacing over everything in insert mode
set autoindent    " always set autoindenting on
"set copyindent    " copy the previous indentation on autoindenting
"set number        " always show line numbers
set shiftwidth=4  " number of spaces to use for autoindenting
"set shiftround    " use multiple of shiftwidth when indenting with '<' and '>'
set showmatch     " set show matching parenthesis
set gdefault      " add /g to replace by default
set ignorecase    " ignore case when searching
set smartcase     " ignore case if search pattern is all lowercase,
                  "    case-sensitive otherwise
"set smarttab      " insert tabs on the start of a line according to
                  "    shiftwidth, not tabstop
set hlsearch      " highlight search terms
set incsearch     " show search matches as you type

set expandtab
set encoding=utf-8
set scrolloff=3
set showmode
set showcmd
set hidden
set wildmenu
set wildmode=list:longest
set visualbell
set cursorline
set ttyfast
set ruler
set backspace=indent,eol,start
set laststatus=2
set relativenumber
set undofile

" Wrapping
set wrap
set textwidth=79
set formatoptions=qrn1
set colorcolumn=85
au BufRead ~/.mutt* set tw=72

" Writing tocs
au BufRead *.rst set tw=0

" Autosave
au FocusLost * :wa

" Python
autocmd FileType python autocmd BufWritePre <buffer> StripWhitespace
