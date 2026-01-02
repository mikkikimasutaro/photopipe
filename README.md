# Photo Viewer

A web application for viewing photos, built with Node.js and Firebase.


## Uses Scripts

sudo mount -t cifs //landisk-0c2790.local/disk1 /mnt/landisk -o guest,iocharset=utf8

source scripts/.venv/bin/activate

python3 scripts/import_photos.py --input-dir /mnt/landisk/Pictures/2014-02-03～16　新婚旅行/ --root-path 新婚旅行 --bucket mikkikicom.firebasestorage.app --service-account mikkikicom-firebase-adminsdk-fbsvc-06bdbf6b0d.json

