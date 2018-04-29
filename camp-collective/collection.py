class Collection:
    amount = None
    items = None
    last_token = None

    def __init__(self):
        self.items = dict()

    def extend(self, items, download_urls):
        for item in items:
            download_url_id = item['sale_item_type'] + \
                str(item['sale_item_id'])
            if download_url_id not in download_urls:
                continue

            obj = Item()
            obj.id = download_url_id
            obj.download_url = download_urls[download_url_id]
            obj.name = item['item_title']
            obj.artist = item['band_name']
            obj.url = item['item_url']
            obj.type = item['item_type']

            self.items[obj.id] = obj


class Item:
    id = None
    download_url = None
    name = None
    type = None
    artist = None
    url = None

    def as_dict(self):
        return dict(self.__dict__)
