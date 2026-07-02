# es常见命令

## postman

- 选择Basic Auth

## 上传文档

```other
curl --location '10.21.10.152:9200/user_order_loyalty2/_doc/002' \
--header 'Content-Type: application/json' \
--header 'Authorization: Basic ZXNfd3JpdGVyOnYzZ0VMaU1tTmlZUVFwVA==' \
--data '{
    "f_user_id":29522159,   
    "f_charge_station_code":"WJY270-BJ49976",
    "is_loyalty":1
}'
```

## 创建索引

```other
curl --location --request PUT '10.21.10.152:9200/user_order_loyalty2' \
--header 'Content-Type: application/json' \
--header 'Authorization: Basic ZXNfd3JpdGVyOnYzZ0VMaU1tTmlZUVFwVA==' \
--data '
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
      "product_name": {
        "type": "text"
      },
      "f_charge_station_code": {
        "type": "keyword"
      },
      "userId": {
        "type": "integer"
      },
      "is_loyalty": {
        "type": "integer"
      }
    }
  }
}
'
```