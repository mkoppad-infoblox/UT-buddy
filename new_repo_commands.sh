# First check the current remote URL
git remote -v

# Remove the existing remote
git remote remove origin

# Add the remote with your renamed repository name
# Replace with your actual renamed repository URL
git remote add origin https://github.com/mkoppad-infoblox/UT-buddy.git

# Verify the new remote URL
git remote -v

# Push to the new remote
git push -u origin main
