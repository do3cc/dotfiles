set nocompatible
" Dein config
set runtimepath+=/home/do3cc/.cache/dein/repos/github.com/Shougo/dein.vim
call dein#begin('/home/do3cc/.cache/dein')
call dein#add('/home/do3cc/.cache/dein/repos/github.com/Shougo/dein.vim')

call dein#add('https://github.com/mattn/emmet-vim/')  " Emmet
call dein#add('osyo-manga/vim-over')  " visual find and replace
call dein#add('ctrlpvim/ctrlp.vim')       " findfiles
call dein#add('preservim/nerdtree')  " navigation
call dein#add('gu-fan/riv.vim')        " rst
call dein#add('vim-syntastic/syntastic') " syntax checker
call dein#add('ntpeters/vim-better-whitespace') " highlight trailing white space
call dein#add('bkad/CamelCaseMotion') " Camelcase moving
call dein#add('vim-airline/vim-airline')    " statusbar hip
call dein#add('vim-airline/vim-airline-themes')    " statusbar hip
call dein#add('justinmk/vim-sneak')   " regex preview
call dein#add('altercation/vim-colors-solarized') " colorscheme
call dein#add('dense-analysis/ale') " Generic linter
call dein#add('christoomey/vim-tmux-navigator') " tmux integration
call dein#add('fatih/vim-go') " Go support
call dein#add('neoclide/coc.nvim', { 'merged': 0, 'rev': 'release' })  " Autocomplete
call dein#end()

filetype plugin indent on

if dein#check_install()
 call dein#install()
endif

" neovim shall not use venv python
let g:python3_host_prog = '/usr/bin/python3'

set autoindent    " always set autoindenting on
set autoread      " Read open files again when changed outside Vim
set noswapfile    " We need no swap file
set backspace=indent,eol,start  " Backspacing over everything in insert mode
set listchars=""       " Empty the listchars
set listchars=tab:>.   " A tab will be displayed as >...
set listchars+=trail:. " Trailing white spaces will be displayed as .
set cursorline    "Show current editor line
set encoding=utf-8
set expandtab     " Convert tabs to spaces
set gdefault      " add /g to replace by default
set hidden        " Don't unload window when not visible
set hlsearch      " highlight search terms
set ignorecase    " ignore case when searching
set incsearch     " show search matches as you type
set laststatus=2  " status line is always visible
set modelines=0   " Ignore vim setting in start of file
set relativenumber " Show relative numbers
set ruler         " Show info of cursor position
set scrolloff=3   " When scrolling, keep this number of lines visible below
set shiftwidth=4  " number of spaces to use for autoindenting
set showcmd       " Show current command
set showmatch     " set show matching parenthesis
set noshowmode    " Don't current mode
set smartcase     " ignore case if search pattern is all lowercase,
set tabstop=4     " a tab is four spaces
set ttyfast       " Fast tty
set undofile      " persistent undo
set visualbell    " Dont beep, make it visual
set wildmenu      " better completion on commands
set wildignore=*.swp,*.bak,*.pyc,*.class,tmp/**,dist/**,node_modules/**  " wildmenu: ignore these extensions
set shell=bash    " Required to let zsh know how to run things on command line
set wildmode=list:longest
set showbreak=↪\
set ttimeoutlen=50

" Wrapping
set wrap
set textwidth=79
set formatoptions=qrn1
set colorcolumn=85
au BufRead ~/.mutt* set tw=72

" remappings
let mapleader=" "
set pastetoggle=<leader>p  " Toggle paste mode

" Writing tocs
au BufRead *.rst set tw=0

" Autosave
au FocusLost * :wa

" Python
autocmd FileType python autocmd BufWritePre <buffer> StripWhitespace

" Rst
autocmd BufRead,BufNewFile *.rst setfiletype rst setlocal nowrap

" Colors
syntax enable
set background=dark
colorscheme solarized
"set t_Co=256      " 256 colors
let g:airline_powerline_fonts = 1
"let g:solarized_termcolors = &t_Co
"let g:solarized_termtrans = 1
"let g:solarized_visibility = "high"
"let g:solarized_contrast = "high"
set background=dark

" Airline
let g:airline_theme='solarized'                   " Use the custom theme I wrote
let g:airline_solarized_bg='dark'
let g:airline_left_sep=''                           " No separator as they seem to look funky
let g:airline_right_sep=''                          " No separator as they seem to look funky
let g:airline#extensions#branch#enabled = 0         " Do not show the git branch in the status line
let g:airline#extensions#syntastic#enabled = 1      " Do show syntastic warnings in the status line
let g:airline#extensions#tabline#show_buffers = 0   " Do not list buffers in the status line
let g:airline_section_x = ''                        " Do not list the filetype or virtualenv in the status line
let g:airline_section_y = '[R%04l,C%04v] [LEN=%L]'  " Replace file encoding and file format info with fileosition
let g:airline_section_z = ''                        " Do not show the default fileosition info
let g:airline#extensions#virtualenv#enabled = 0

" Resize windows
nnoremap <Left> :vertical resize +1<CR>
nnoremap <Right> :vertical resize -1<CR>
nnoremap <Up> :resize +1<CR>
nnoremap <Down> :resize -1<CR>

" Visual find and replace
nnoremap <Leader>fr :call VisualFindAndReplace()<CR>
xnoremap <Leader>fr :call VisualFindAndReplaceWithSelection()<CR>
function! VisualFindAndReplace()
    :OverCommandLine%s/
    :w
endfunction
function! VisualFindAndReplaceWithSelection() range
    :'<,'>OverCommandLine s/
    :w
endfunction

" Force write
cmap w!! w !sudo tee %

" syntastic checks
let g:syntastic_check_on_open=1                   " check for errors when file is loaded
let g:syntastic_loc_list_height=5                 " the height of the error list defaults to 10
let g:syntastic_python_checkers = ['flake8']      " sets flake8 as the default for checkingython files
let g:syntastic_javascript_checkers = ['jshint']  " sets jshint as our javascript linter
let g:syntastic_filetype_map = { 'handlebars.html': 'handlebars' }
let g:syntastic_mode_map={ 'mode': 'active',
                     \ 'active_filetypes': [],
                     \ 'passive_filetypes': ['html', 'handlebars'] }

" ALE Linting config
let g:ale_fixers = {
            \'javascript': ['prettier', 'eslint'],
            \'typescriptreact': ['prettier', 'tslint'],
            \'python': ['black', 'isort'],
            \'*': ['remove_trailing_lines', 'trim_whitespace']
            \}
let g:ale_fix_on_save = 1

" ctrlp config
let g:ctrlp_use_caching=0
let g:ctrlp_custom_ignore = '\v[\/](transpiled)|dist|tmp|node_modules|(\.(swp|git|bak|pyc|DS_Store))$|lib|lib64|share|bin'
let g:ctrlp_working_path_mode = 0
let g:ctrlp_max_files=0
let g:ctrlp_max_height = 18
let g:ctrlp_open_multiple_files = '1vjr'
let g:ctrlp_buffer_func = { 'enter': 'MyCtrlPMappings' }
nnoremap <Leader>ff :CtrlP<CR>
map <Leader>fs :CtrlPTag<CR>
map <Leader>fd :CtrlPCurFile<CR>
map <Leader>fb :CtrlPBuffer<CR>
func! MyCtrlPMappings()
    nnoremap <buffer> <silent> <F6> :call <sid>DeleteBuffer()<cr>
endfunc

" Nerdtree
let NERDTreeIgnore = ['\.pyc$']
let g:NERDTreeMapJumpNextSibling = ''
let g:NERDTreeMapJumpPrevSibling = ''
map <Leader>d :NERDTreeToggle<CR>
nmap <Leader>nt :NERDTreeFind<CR>

" Configure emmet
let g:user_emmet_install_global = 0
