# Описание

Sapfir2MQTT является посредником (gate) между устройствами Sapfir и MQTT сервером, что позволяет управлять устройствами Sapfir и получать показания со встроенных датчиков с использованием любого совместимого MQTT клиента.

Sapfir2MQTT производит обмен данными с устройством, используя протокол локального управления Sapfir, фильтрует сигналы и транслирует в обе стороны сигналы с полезной для пользователя смысловой нагрузкой через встроенный MQTT клиент на MQTT сервер.

# Список зависимостей

Для работы Sapfir2MQTT необходимы:

1. Python3
2. Библиотеки python3:
	- paho.mqtt (не ниже версии 1.4)
	- asyncio
	- socket
	- yaml
	- json
	- time
2. Сервер MQTT

# Установка

## Debian based linux (ubuntu, debian, mint и т.п.)
```
sudo apt-get update
sudo apt-get install python3 python3-pip python3-yaml
sudo pip3 install paho-mqtt
```

# Запуск

Для запуска Sapfir2MQTT требуется наличие конфигурационного файла. Файл должен иметь имя config.yml и находиться в директории, из которой производится запуск. Формат файла должен соответствовать стандарту синтаксиса [YAML](https://yaml.org/spec/1.2/spec.html).

Пример конфигурационного файла:
```
mqtt:  
	host: 127.0.0.1  
	password: 'password'  
	port: 1883  
	user: 'user'
sapfirlocal:  
	addresses:  
	host: 0.0.0.0  
	pkgmaxlen: 4096
	loglevel: INFO
	processing_interval: 0.05  
	tokens:
```

Описание параметров конфигурационного файла:
```
mqtt:
  	host: адрес MQTT-сервера
  	password: пароль MQTT-клиента (опционально)
  	port: порт MQTT-сервера
  	user: имя MQTT-клиента (опционально)
sapfirlocal:
  	addresses: секция для хранения IP-адресов конечных устройств (заполняется автоматически)
  	host: адрес интерфейса для приема UDP-пакетов
  	pkgmaxlen: ограничение длины принимаемого пакета (не изменяйте этот параметр без необходимости)
  	loglevel: уровень логирования, может принимать значения DEBUG/INFO/NOTICE/WARNING/ERROR/CRITICAL
  	processing_interval: пауза в работе UDP-сервера, необходимая для корректной работы асихронных методов (не изменяйте этот параметр без необходимости)
	tokens: секция для хранения токенов конечных устройств (заполняется автоматически)

```

Непосредственно запуск должен производиться из директории, в которой расположен скрипт sapfir2mqtt.py и конфигурационный файл config.yml:
```
$ ./sapfir2mqtt.py
```

# Подключение устройств

Для взаимодействия с устройством необходимо знать его серийный номер. Он должен быть нанесен на заднюю сторону устройства. В случае, если номер отсутствует или в силу объективных причин к задней стороне устройства невозможно получить доступ, следует дождаться получения пакета от устройства, серийный номер будет содержаться в данных пакета. В случае подключения нескольких устройств, выяснить соответствие устройств и серийных номеров можно, основываясь на полученных из пакета данных (статусы каналов, название модели, события нажатий на кнопки и т.п.).

Для отправки данных на устройство, с целью изменения его статуса, помимо серийного номера требуется токен.

<a name="token"></a>Получение токена возможно двумя способами:

1. Устройство отправляет токен раз в некоторый период времени (в зависимости от типа устройства и прошивки это может происходить раз в час, шесть или 12 часов) в составе пакета с данными - достаточно дождаться отправки токена устройством;

2. Устройство отправляет токен в составе пакета с данными после перезагрузки.

3. В поледних прошивках устройство отправляет токен в каждом пвкете.

Для перезагрузки устройства следует удерживать кнопку настройки или центральную кнопку до 4 звуковых или световых сигналов, если нет кнопки настройки либо по каким-либо иным причинам не удается добиться перезагрузки устройства, необходимо временно прервать подачу питания на устройство.

# Настройка устройств
Реле и управляемые розетки не требуют каких-либо дополнительных настроек. В случае использования диммера необходимо учитывать, что он может работать в двух режимах - режиме включения/выключения и режиме диммирования.
Для включения света в первом режиме необходимо присвоить сигналу с именем lamp-aN (где N - номер канала управления) значение 100, для отключения - 0. 
При использовании режима диммирования возможно присвоение сигналу lamp-aN значений в промежутке от 0 до 100, где нулевое значение сигнала приведёт к полному отключению освещения, а значение сигнала равное 100 будет соответствовать полной яркости.
Для переключения устройства в режим диммирования используется сигнал - reg-dmx-aN (где N - номер канала).

Пример пакета для включения диммирования:

```
{"command":"management","id":2797185,"uniq_id":47486,"token":"02d1442c4a9af0840889821885c2a72","reg-dmx-a1":1}
```


# Описание принципов взаимодействия

### Описание работы протокола UDP

Устройства посылают UDP пакеты раз в минуту. Заголовок пакета содержит адрес, тело пакета - набор данных, отправленных устройством.

Пример набора данных:

```
{'id': 823600, 'devName': 'msensor_m2', 'data': {'uniq_id': 0, 'ver': '9', 'cs': 240, 'light': 1024, 'light-en': 1, 'led-adpt': False, 'capt-ir-raw': False, 'push-w': 1563347773, 'term': 30.20742, 'hum': 44.66722, 'term-en': 1, 'pir-time': 1563360661, 'pir': True, 'pir-en': 1, 'mic-tm-set': 100000, 'mictime': 1563349166, 'micvalue': 0, 'mic-en': 1, 'ping': '78,66,4', 'tcp-state': 3, 'cur-ch': 6, 'time': 1563360661, 'stat': 2, 'rssi': -61, 'hp': 28720}}
```

Значения основных полей:

- id - серийный номер устройства
- devName - модель устройства
- data - набор сигналов с соответствующими им значениями

Для отправки пакета конкретному устройству требуется его IP адрес, [токен](#token) и уникальный идентификатор запроса uniq_id. Поле uniq_id используется для идентификации ответа устройством на запрос и принимает положительные целочисленные значения, соответствующие размеру в 4 байта. После отправки сообщения, содержащего поле uniq_id, в последующих принятых пакетах должен быть получен пакет с идентичным значением поля uniq_id в наборе данных data. Это используется для сравнения отправленных и полученных значений прочих полей и вывода дополнительного сообщения в случае их несоответствия.

Пример пакета для отправки:

```
{"command":"management","id":2797185,"uniq_id":32865,"token":"02d1442c4a9af0840889821885c2a72","rele1":1}
```

Где rele1 - имя сигнала, у которого необходимо поменять значение.

Пример ответа:

```
{'uniq_id': 32865, 'ver': '16', 'cs': 60, 'n': 5926, 'push1': 1563525716, 'tm_rele1': 0, 'rele1': 1, 'push2': 1563525712, 'tm_rele2': 0, 'rele2': 0, 'in1': 0, 'in2': 0, 'adc': 1024, 'in1t': 0, 'in2t': 0, 'term-sex': 5.733438, 'sex-en': True, 't-en': 0, 'ping': '57,48,2', 'stat': 3, 'scen': 0, 'ip': '192.168.254.169', 'time': 1563525731, 'rssi': -59, 'cur-ch': 6, 'hp': 32600}
```


### Описание работы программы

Класс Mqtt устанавливает соединение с сервером и подписывается на топик /sapfir.

Класс SapfirLocal принимает UDP пакеты с устройств, обрабатывает полученные данные. Сохраняет адрес и токен в конфигурационном файле, а также данные о сигналах устройств в памяти программы.

При изменении данных какого-либо сигнала в классе Sapfir2MQTT проверяется его отсутствие в списке blacklist, если сигнал отсуствует в данном списке, происходит публикация его значения в топик /sapfir/XXXXXX/signalname, где XXXXXX - это серийный номер устройства, а signalname - имя сигнала. При публикации в данный MQTT топик нового значения приложение сформирует и отправит UDP пакет необходимого содержания на устройство с соответствующим серийным номером. Если сигнал является изменяемым, устройство должно принять его новое значение. 

При получении публикации по сигналу, имеющемся в списке modifablelist, происходит отправка пакета устройству по UDP для изменения значения сигнала. 

Пример темы:

```
общий топик/серийный номер устройства/имя сигнала
```

# Описание сигналов

| Имя | Описание | Тип данных | Значения | Пример |
|:----|:----------|:----|:----|:----|
| pir-time | Время последнего движения | time, sec | -> | 1563276026 |
| n | Номер пакета | int | -> | 5 |
| r-dtrl | Антидребезг кнопок управления | int, ms | -> | 100 |
| coff-term | Коррекция | int | -> | 0 |
| rele1 | Канал управления 1 | int | 0/1 | 1 |
| rele2 | Канал управления 2 | int | 0/1 | 1 |
| in1-inv | Инвертировать состояние входа 1 | int | 0/1 | 1 |
| light-en | Датчик освещённости установлен | int | 0/1 | 1 |
| micvalue | Текущий уровень датчика звука | int, msec | -> | 0 |
| in2-inv | Инвертировать состояние входа 2 | int | 0/1 | 1 |
| ver | Версия микропрограммы | string | -> | '16' |
| tm_rele1 | Таймер реле 1 | time, sec | -> | 0 |
| tint-en | Использовать показания собственного датчика температуры для регулирования | int | 0/1 | 1 |
| t-en | Датчик температуры установлен | int | 0/1 | 1 |
| in2 | Состояние входа 2 | int | 0/1 | 1 |
| in2c | Действие при замыкании входа 2 | int | 0-OF/1-1N/2-2N/3-ALN/4-1I/5-2I/6-ALI | 2 |
| token | Токен для локального управления | string | -> | 'c2f0c00f5f95821c716bc44d4986528' |
| ip | IP Адрес | string | -> | '192.168.254.169' |
| inrt2 | Инерционность, канал 2 | int, sec | -> | 0 |
| treg | Поддерживаемая температура | int, °С | -> | 24 |
| in2t | Время изменения состояния порта 2 | int, sec | -> | 0 |
| en-udp | Локальный UDP коммуникатор | int | 0/1 | 1 |
| in1o | Действие при размыкании входа 1 | int | 0-OF/1-1F/2-2F/3-ALF/4-1I/5-2I/6-ALI | 1 |
| in1 | Состояние входа 1 | int | 0/1 | 1 |
| adc | Значение АЦП | int | -> | 1024 |
| in1c | Действие при замыкании входа 1 | int | 0-OF/1-1N/2-2N/3-ALN/4-1I/5-2I/6-ALI | 1 |
| in1t | Время изменения состояния порта 1 | time, sec | -> | 0 |
| tcp-state | Состояние сокетов | int | -> | 3 |
| hum | Влажность воздуха | float, % | -> | 54.96599 |
| aref | Порог АЦП для изменения состояния входа | int          | -> | 512 |
| in2o | Действие при размыкании входа 2 | int | 0-OF/1-1F/2-2F/3-ALF/4-1I/5-2I/6-ALI | 2 |
| en-tcp | Облачный TCP коммуникатор | int | 0/1 | 1 |
| pir-en | Датчик движения установлен | int | 0/1 | 1 |
| mic-en | Датчик звука установлен | int | 0/1 | 1 |
| micwnd | Длительность окна замера импульсов микрофона | int, msec | -> | 300 |
| inrt1 | Инерционность, канал 1 | int, sec | -> | 0 |
| cur-ch | Канал WiFi | int | -> | 6 |
| term-en | Датчик температуры и влажности установлен | int | 0/1 | 1 |
| pir | Датчик движения | bool | True/False | False |
| rssi | Уровень сигнала | int, % | -> | -58 |
| sex-en | Датчик температуры пола установлен | bool | True/False | True |
| coff-ntc | Коррекция NTC датчика | int | -> | 0 |
| push1 | Кнопка управления 1 | time | -> | 1563344410 |
| led-stat | Индикация | int        | -> | 3 |
| time-utc | Смещение часового пояса | int, min | -> | 0 |
| stat | Состояние работы устройства | on/power | &&& | 2 |
| term-sex | Температура пола | float, °C | -> | 5.733438 |
| mictime | Время срабатывания датчика звука | time | -> | 1563275903 |
| led-adpt | Адаптивная подстветка | bool | True/False | False |
| ntc-beta | Коэффициент B датчика температуры NTC | int | int | 3988 |
| push2 | Кнопка управления 2 | time | -> | 1563344442 |
| ntc-res | Сопротивление датчика температуры NTC | int | -> | 10000 |
| mic-tm-set | Порог срабатывания датчика звука | int, msec | -> | 100000 |
| en-log | Режим логирования | int | 0/1 | 0 |
| term | Температура воздуха | float, °C | -> | 28.41395 |
| tm_rele2 | Таймер реле 2 | int, sec | -> | 0 |
| treg-en | Включить регулирование температуры | int | 0/1 | 0 |
| capt-ir-raw | Режим захвата команды ИК пульта | bool | True/False | False |
| hp | Индикатор свободной памяти | int, byte | -> | 28880 |
| cs | Интервал контрольных сеансов | int, sec | -> | 240 |
| time | Встроенные часы | time | -> | 1563276154 |
| rele1-inv | Управление реле 1 инвертировано | int | 0/1 | 1 |
| rele2-inv | Управление реле 2 инвертировано | int | 0/1 | 1 |
| ping | Пинг серверов | string, ms | -> | '57,35,2' |
| light | Освещённость | int, % | -> | 1024 |
| led-bright | Яркость индикации | int | -> | 100 |
| scen | Выполнить сценарий | int | -> | 0 |
| upd-scen | Время обновления сценариев | int              | -> | 1563272349 |
| tmxs2  | Ограничение температуры нагревателя | int, °C | -> | 255 |
| tb-type | Источник показаний температуры | int, off/air/ext | &&& | 0 |
| uniq_id | Уникальный идентификатор для связи запроса к устройству и ответа от него | int | -> | 12345 |
| terev | Действие при ошибке датчика температуры | int | -> | 255 |
| thiev | Действие при повышении температуры | int | -> | 255 |
| tlwev | Действие при понижении температуры | int | -> | 255 |
| in1tc | Установить таймер при замыкании входа 1 | int, sec | -> | 0 |
| in2tc | Установить таймер при замыкании входа 2 | int, sec | -> | 0 |
| in1to | Установить таймер при замыкании входа 1 | int, sec | -> | 11684 |
| in2to | Установить таймер при размыкании входа 2 | int, sec | -> | 0 |
| in1ct | Действие, при истечении таймера на замыкание входа 1 | int | -> | 255 |
| in2ct | Действие, при истечении таймера на замыкание входа 2 | int | -> | 255 |
| in1ot | Действие, при истечении таймера на размыкание входа 1 | int | -> | 255 |
| in2ot | Действие, при истечении таймера на размыкание входа 2 | int | -> | 255 |
| reg-term | Средняя температура датчика | float, °C | -> | 29.91847 |
| pwr-in | Входное напряжение | float | -> | 332.2 |
| tmr-aoff2 | Время до автовыключения освещения, канал 2 | int, min | -> | 0 |
| pwr-brd | Напряжение питания драйвера | float | -> | 3.615 |
| hw-pb | Тип платы питания | int | -> | 3 |
| fw-pb | Версия микропрограммы платы питания | int | -> | 2 |
| pb-en | Подключена дополнительная плата питания | bool | True/False | True |
| lamp_a1 | Освещение, канал 1 | int, % | -> | 0 |
| brd-term | Температура платы | float, °C | -> | 39.9 |
| lamp_a2 | Освещение, канал 2 | int, % | -> | 0 |
| rele-wt | Заданное состояние нагревателя | bool             | True/False | True |
| sn-btn2-en | Сенсорная кнопка 2 установлена | int | 0/1 | 1 |
| push-w | Сенсорная кнопка | time | -> | 1563442883 |
| push-w2 | Нижняя правая сенсорная кнопка | time | -> | 1563442634 |
| s | Размер основного пакета | int | -> | 524 |
| ai-al | Расчётный уровень освещённости | int, % | -> | -1 |
| tmr-aoff1 | Время до автовыключения освещения, канал 1 | int, min | -> | 0 |
| mts | Порог срабатывания датчика звука | int, msec | -> | 100000 |
| rele-t | В данный момент подогрев | bool | True/False | True |
| mt | Время срабатывания датчика звука | time | -> | 1563445741 |
| mv | Текущий уровень датчика звука | int, msec | -> | 0 |
| tf | Есть актуальные показания температуры воздуха для регулятора | int | 0/1 | 1 |
| reg-dmx-a1 | Диммирование, канал 1 | int | 0/1 | 1 |
| reg-dmx-a2 | Диммирование, канал 2 | int | 0/1 | 1 |

# Описание устройств 

| Модель | Внутреннее имя | Сигналы (чтение/запись) |
|:----|:----|:----------|
| Мультисенсор SAPFIR | msensor_m2 | uniq_id(rw), ver(r), cs(rw), light(r), light-en(rw), led-adpt(rw), capt-ir-raw(rw), term(r), hum(r), coff-term(rw), term-en(r), pir-en(r), mic-en(r), led-bright(rw), en-udp(rw), en-tcp(r), en-log(rw), led-stat(rw), time-utc(rw), ping(r), tcp-state(r), cur-ch(r), rsrv(r), token(r), ip(r), time(r), stat(r), rssi(r), hp(r), id(), mic-tm-set(rw), micwnd(rw), mictime(r), micvalue(r) |
| 2-х канальное реле SAPFIR | dinRelay_m2 | uniq_id(rw), ver(r), cs(rw), n(r), tm_rele1(rw), rele1(rw), tm_rele2(rw), rele2(rw), rele1-inv(rw), rele2-inv(rw), r-dtrl(rw), inrt1(rw), inrt2(rw), in1(r), in2(r), adc(r), in1t(r), in2t(rw), term-sex(r), sex-en(r), t-en(r), tb-type(rw), treg-en(rw), tint-en(rw), treg(rw), tmxs2(rw), terev(rw), thiev(rw), tlwev(rw), en-udp(rw), en-tcp(r), time-utc(rw), upd-scen(rw), in1-inv(rw), in2-inv(rw), in1c(rw), in1o(rw), in2c(rw), in2o(rw), in1tc(rw), in2tc(rw), in1to(rw), in2to(rw), in1ct(rw), in2ct(rw), in1ot(rw), in2ot(rw), aref(rw), coff-ntc(rw), ntc-res(rw), ntc-beta(rw), scen(rw), hp(r), push1(r), push2(r), token(r) |
| Диммер - выключатель SAPFIR | sdimmer_m2 | pir-time(r), n(r), light-en(rw), pwr-in(r), ver(r), tmr-aoff2(r), pwr-brd(r), hum(r), pir-en(r), hw-pb(r), fw-pb(r), mic-en(r), pb-en(r), lamp_a1(rw), term-en(r), brd-term(r), pir(r), lamp_a2(rw), rssi(r), stat(r), sn-btn2-en(rw), push-w(r), term(r), capt-ir-raw(rw), hp(r), cs(rw), time(r), ping(r), s(r), ai-al(r), tmr-aoff1(r), scen(rw), mts(rw), mt(r), mv(r), token(r) |
| Датчик протечки беспроводной SAPFIR | ldsensor_m2 | n(r), light-en(rw), ver(r), tcp-state(r), pir-en(r), mic-en(r), cur-ch(r), term-en(r), rssi(r), stat(r), capt-ir-raw(rw), hp(r), cs(rw), time(r), ping(r), token(r) |
| Термостат - регулятор тепла SAPFIR | termostat_m2 | reg-term(r), n(r), light-en(rw), ver(r), hum(r), pir-en(r), mic-en(r), term-en(r), rssi(r), rele-wt(rw), sex-en(r), stat(r), term-sex(r), sn-btn2-en(rw), push-w(r), push-w2(r), term(r), capt-ir-raw(rw), hp(r), cs(rw), time(r), ping(r), s(r), scen(rw), rele-t(r), tf(r), token(r) |
| Умная внешняя розетка SAPFIR | sonoff_ext_socket | reg-term(r), n(r), light-en(rw), ver(r), hum(r), pir-en(r), mic-en(r), term-en(r), rssi(r), rele-wt(rw), sex-en(r), stat(r), term-sex(r), sn-btn2-en(rw), push-w(r), push-w2(r), term(r), capt-ir-raw(rw), hp(r), cs(rw), time(r), ping(r), s(r), scen(rw), rele-t(r), tf(r), token(r) |
