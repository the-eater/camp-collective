from datetime import datetime

class Collection:
    amount = None
    items = None
    last_token = None
    enrichment = None

    def __init__(self):
        self.items = dict()
        self.enrichment = dict()

    def set_enrichment(self, enrichment):
        if enrichment["collection_summary"] and enrichment["collection_summary"]["tralbum_lookup"]:
            self.enrichment = enrichment["collection_summary"]["tralbum_lookup"]

    def extend(self, items, download_urls):
        for item in items:
            download_url_id = item['sale_item_type'] + \
                str(item['sale_item_id'])
            if download_url_id not in download_urls:
                continue

            item_id = download_url_id
            item_type = item['item_type']

            if item['sale_item_type'] == 'p':
                item_type = item['tralbum_type']
                item_id = item['tralbum_type'] + str(item['tralbum_id'])

            if 'purchased' not in item and item_id in self.enrichment:
                item['purchased'] = self.enrichment[item_id].get('purchased', None)

            obj = Item()
            obj.id = download_url_id
            obj.item_id = item_id
            obj.download_url = download_urls[download_url_id]
            obj.name = item['item_title']
            try:
                obj.purchased = datetime.strptime(item['purchased'], "%d %b %Y %H:%M:%S %Z")
            except:
                pass

            obj.artist = item['band_name']
            obj.url = item['item_url']
            obj.type = item['item_type']

            self.items[obj.id] = obj


class Item:
    id = None
    download_url = None
    item_id = None
    purchased = None
    name = None
    item_type = None
    type = None
    artist = None
    url = None

    def as_dict(self):
        obj = dict(self.__dict__)
        if self.purchased is not None:
            obj["purchased"] = self.purchased.isoformat()
        return obj
