# Python packages I use in every project
packages=( 
    checkoutmanager 
    zest.releaser 
    check-manifest 
    zest.pocompile
    checkoutmanager
    )

for package in "${packages[@]}"; do
    sudo pip install -U "$package"
done
