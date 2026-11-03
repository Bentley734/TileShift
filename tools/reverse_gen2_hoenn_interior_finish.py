"""Explicit complete Crystal counterparts for native RSE interior tile banks.

GBA atlas rows remain pair-global. Existing reverse themes and complete earlier
rooms are immutable; every new alias checks native indexed layers and behavior.
"""
import argparse,copy,json,re
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import catalog,preview
from reverse_common import ReverseReview,ROOT
from reverse_hoenn_review import native_geometry,donor_ref
from reverse_kanto_review import exterior,runs
from building_review import decode_layout
from reverse_gen2_kanto_finish import classic_floor_symbol

GAMES=('ruby','sapphire','emerald')
TARGET=ROOT/'mappings/reverse_gen2_hoenn_interior_finish.lua'
GENERAL_INTERIORS={'general__bike_shop','general__inside_of_truck','general__ship','general__inside_ship',
 'general__contest','general__battle_palace','general__battle_tent','general__battle_frontier','general__facility'}
FACILITY_OUTDOORS={804,805,808,809,810,811,812,813,814,815,816,817,818,823,824,825,826,827,828,829,830,831,832,833,834,835,
 702,703,718,719,819,820,861,947,968,969,970,971,972,973}

SURFACE_CONTRACTS=[
    ('building__trick_house_puzzle', 520, '9bb3156d04612784902307b8586394f654cfbd7c40d64cb765003a153c7d3f9d', 'tatami'),
    ('building__generic_building', 547, '4aa4fe87532dfa6a1593926474f2eea8856406e5b73937bd42a15946b6f352ba', 'wood'),
    ('general__facility', 552, '132e278fc5123d96c22b3efbd3dbb4d5f8499af74082c7fc81189ef2772ef5c4', 'facility'),
    ('building__contest', 608, '776590443546cd5b4b97251b84432afd1c727e7f9cf3b70b5536860b5bc964e9', 'facility'),
    ('general__inside_ship', 568, 'c4ea551bf87c001d7f414d3e328711cd4bc329654d5cd610daaa61051e536869', 'ship'),
    ('general__facility', 553, '8f59ec070c6fb8be0947f7c6ef6b23d6f7b3dc364d917ad4dc2bdf57d7fb7090', 'facility'),
    ('general__facility', 514, '4708b4af04323fa57576729a533cf324cab93d18913ca8275bc56359bcbeecd2', 'facility'),
    ('general__facility', 742, 'e8f8fa5820e1bd9e963d934e129a696cd9e4bf48813f44b18f2cf8306cb71527', 'stone'),
    ('general__facility', 545, 'be16a3cc28a4b368ef8d498c822c96e100bf1c4b398403948fd558d748bb27bb', 'wall_facility'),
    ('general__facility', 736, 'cf34b4ae536a56c7364275d531ff87fc9547f246214da4ae7595b5b4d46dc8c9', 'wall_facility'),
    ('secret_base__secret_base_yellow_cave', 522, 'a4c659694f4cccdef3ff137f10579ee9305e2bc5a86f8c22a6066757d513d8ea', 'cave'),
    ('secret_base__secret_base_brown_cave', 522, '18f355ce7c7abbd61ce92b8c5f098f3f9256819bb01001b0301214911b44f697', 'cave'),
    ('secret_base__secret_base_shrub', 522, '5482eb8140786ac0c724acdb0e268c50a2868c6b277283638481f2973d3b42ef', 'cave'),
    ('secret_base__secret_base_tree', 522, '9ebc2819159085e3abd7cd76c0a17cc45771d46f20bff407628169832e36cbb2', 'wood'),
    ('general__contest', 549, 'e05ea7f078b705f8f202d4235a81a1960e299396bcac144a5e0d42928a9998c4', 'facility'),
    ('general__bike_shop', 528, '2ab15e61b32051abbc5fa8eb4c0a93dbdbf1375de28f5f3cee8dd2fa6e11e6fa', 'stone'),
    ('general__facility', 752, '2ac24e12d7c0b63ef99be5a5c9c42bacc69db0fc0d6d4ac99765e6b61bd63c59', 'stone'),
    ('building__lavaridge_gym', 520, 'efb7d04288f46ce4730da33c19c58db45bf736f1ae9d3024dc438cb4ee21cfad', 'blue_tile'),
    ('secret_base__secret_base_blue_cave', 522, 'a6bdc802827e9d0aab065565133ce8ef5c88fdc55599593d327fef851715c6b0', 'cave'),
    ('general__facility', 601, '5ddef4727ca902ebe3abe0c42b3e7949bd949cfa1213f579525e4892abd08689', 'facility'),
    ('building__generic_building', 517, 'b73bdd5eae74399030dc9c9559357c96d2d24024bb0f3dda87a5ea78395565d4', 'wall_house'),
    ('secret_base__secret_base_red_cave', 522, '226a875cc38a70491c0113db8747ad0ef36abf0a8f0b993325d880ce2a8b4bca', 'cave'),
    ('general__inside_ship', 571, '5bcca8e5a647eb4ad8b560e879a09242871984bae725b5d5fd055f821532247e', 'ship'),
    ('building__generic_building', 1022, '385260b6bb7d7d9d6fca67307cc86dc47113728457ca61940c1573cf7ef4cba1', 'stone'),
    ('building__generic_building', 548, '43518653e866324b8a111b3384a904220db5fe7dfa9e5df620aac67e5c592de4', 'wood'),
    ('general__contest', 625, '6d54e379efe79710cd1a3a1fd73ece4f7a26d34ed6193c592a4ad67da36703da', 'facility'),
    ('building__generic_building', 811, '7336090bb8b427983a60f05955edb7a498e942eb6a39fb08b77d61e683760400', 'stone'),
    ('building__generic_building', 569, '72f3e766e4307aeca2a49f21516cfa8a2d4044c6eb0502fffa8e751d23d7fdb8', 'wood'),
    ('building__pokemon_center', 551, '806d7fb0ca3a1bfd8f094ef3fee44342788ea1d359bb75a9cb35d4b9e4fc86d7', 'clinic'),
    ('general__facility', 554, '06cf54b9ea8c70cd7a620992b9b937a8c72440a548a33b39ab733f3e1f517b66', 'facility'),
    ('building__facility', 896, '835f492f80fa71dcdc0257b144f79de158487e8822071104c2704ecfe8e22655', 'facility'),
    ('building__battle_dome', 832, '507856af8acebf9a97010f7cb174908f0ac3bfd8b95d875881f15e85676999dc', 'facility'),
    ('building__battle_dome', 833, '5128c318b149f131655a36d4e3b5d1cf29ec6849a7d838729b8206cdde19bdf6', 'facility'),
    ('building__generic_building', 525, '196b7cb532bab14c16bfdc5dd5e3bb4661d68e5db9f056ffc8f3512d2fe2765c', 'wall_house'),
    ('building__trainer_hill', 875, '07c2140fdac677e2b70de6e16ad54fb53dd621fb809c98f1eed3b344d6a4decc', 'stone'),
    ('general__bike_shop', 567, '14cee1541dfe9dc1d6ebcb07a6c515da05e101e9ae08c50f78e9780a2a441104', 'stone'),
    ('general__inside_ship', 573, '55885ba4df8748e7d2134c270ca6d214f8379c3dec08bd26415c5e8af3786b49', 'ship'),
    ('building__battle_tent', 528, '5e88a0ec262adb875d40da2335bb16967da2805a98abacbf003b1a0880421fb6', 'facility'),
    ('general__inside_ship', 514, '4580960617c12edc5b6d00fb7a868225ea34fa9fb68f5e089c2747f9164001f9', 'ship'),
    ('general__contest', 608, '776590443546cd5b4b97251b84432afd1c727e7f9cf3b70b5536860b5bc964e9', 'facility'),
    ('building__mystery_events_house', 565, '3f4cc7044ceca83a7bf0e86d564ea4dd926ab4a35c3bcb5f3a99dfcd6578533a', 'facility'),
    ('building__battle_pike', 705, 'a4506e2826c686dfb7c30e875752767844d5c35fa141db26ee719be202db2aeb', 'facility'),
    ('building__trick_house_puzzle', 513, '9f5e65a96d1bb91e48ca0c7ad0838cc7db33c44d7ab239cec72e12ee11aa5458', 'wall_facility'),
    ('building__trick_house_puzzle', 642, '4cd4eb61c572e1f3203ed0c4a9a3d49b4763ed07261a743f77ece712910dfbf9', 'wood'),
    ('building__battle_tent', 529, '08bdf1fe0986f5ee802ac791825060c95efe63e2c3fdc0c5ed2d7e430a6e180d', 'facility'),
    ('building__union_room', 531, '4485bfe871e37d22b4aba03d619b589bdea3bbaa8d394a39df986fb8dd432c96', 'link'),
    ('building__generic_building', 795, '4e0db70ac039d8742b859f00acf792fed1ffb74758793b7ad4a4c4ca7386757d', 'house'),
    ('building__lab', 594, 'd9383846c80dbf496f4dc772eb9a2d2a5b168032cd3dd10da33e64aa2e7eecba', 'lab'),
    ('building__trainer_hill', 561, '979f9851302e561449f11d780c75343987c8eb7713e1456720d21bad974c7162', 'tatami'),
    ('building__fortree_gym', 514, '572f170b73748cf59bf73343c9ec2264b0b4c6efd865d7ed83a1c0ad67ae2db9', 'wood'),
    ('building__lavaridge_gym', 521, '6b0a31e99a5f616be890773c80b966503fd440810b131c899bbaef975e91f8a1', 'blue_tile'),
    ('general__facility', 673, 'f49bb8b8ae71b7d2c27acf36b8b420a7e177fc57e990ebd9ed20b48ac5380879', 'facility'),
    ('general__facility', 743, '148cbabcc41c6dfcab4e9e2d9f451425cfe127c864b2977022d842fbfb32727f', 'stone'),
    ('building__shop', 648, '9d70c355dc0853b5e5b7f704b09399ba007cf064c102db6d19ac29dbe4f75bdb', 'wall_facility'),
    ('building__trick_house_puzzle', 528, '35744a2627dfa90fbbbe000b3f7814d552a9fad8b5d35929c9c5818200a450bb', 'tatami'),
    ('building__trick_house_puzzle', 521, 'cdc28da0bf351c1631945e4e06f44ca8d52bd42bc2154daca7e873b9ccbccd3b', 'wall_facility'),
    ('building__contest', 625, '6d54e379efe79710cd1a3a1fd73ece4f7a26d34ed6193c592a4ad67da36703da', 'facility'),
]

PLANT_CONTRACTS=[
    ('ruby', 793, 807, '4b7df1688b71b906ec8c61452d54dd99af9d3004ba4b3ea0546b534992e64c27', 'house'),
    ('ruby', 794, 802, 'ecee6ead38ff7101abbc85e92e0e946333ac6f5fe0643fc312bae360d99323b7', 'house'),
    ('ruby', 656, 664, 'ff4872df817c5ba1abff52c45dd022c7d1f65341b97d5891e6fe2e60d5247aac', 'wood'),
    ('ruby', 546, 554, '5b7042e2b86997b403b4bbee1d1c6feccadeec68d1f191b9ce4771f9c53c50f6', 'wood'),
    ('ruby', 838, 846, '04fce281b65a3a11d191e17df895437f3e6c6da78434c8c972cf40da8787d256', 'stone'),
    ('ruby', 839, 847, 'e67b69deeb683016f28613103bf57571a93a6f4a411bfa91a5f5370316ede3b7', 'stone'),
    ('ruby', 657, 665, '226e41e01d1f91321270cbb76a84709072e56c7e23066ea8ca779001921777af', 'wood'),
    ('ruby', 660, 668, 'd1546c520b6354e1c9635f72b28ea3624f38a851f3bb0394119c801aa596d782', 'stone'),
    ('sapphire', 838, 846, '04fce281b65a3a11d191e17df895437f3e6c6da78434c8c972cf40da8787d256', 'stone'),
    ('sapphire', 839, 847, 'e67b69deeb683016f28613103bf57571a93a6f4a411bfa91a5f5370316ede3b7', 'stone'),
    ('sapphire', 656, 664, 'ff4872df817c5ba1abff52c45dd022c7d1f65341b97d5891e6fe2e60d5247aac', 'wood'),
    ('sapphire', 546, 554, '5b7042e2b86997b403b4bbee1d1c6feccadeec68d1f191b9ce4771f9c53c50f6', 'wood'),
    ('sapphire', 657, 665, '226e41e01d1f91321270cbb76a84709072e56c7e23066ea8ca779001921777af', 'wood'),
    ('sapphire', 660, 668, 'd1546c520b6354e1c9635f72b28ea3624f38a851f3bb0394119c801aa596d782', 'stone'),
    ('sapphire', 793, 807, '4b7df1688b71b906ec8c61452d54dd99af9d3004ba4b3ea0546b534992e64c27', 'house'),
    ('sapphire', 794, 802, 'ecee6ead38ff7101abbc85e92e0e946333ac6f5fe0643fc312bae360d99323b7', 'house'),
    ('emerald', 656, 664, '7367501f7ff1ab78f4f988c77f6f03fef3568243ee9ea7c0e27b4a11f099226d', 'wood'),
    ('emerald', 546, 554, '881cdc6fe8eec66d5e26fb0825a211487e5984a3effb97125fa5bb17ec8e8de2', 'wood'),
    ('emerald', 657, 665, '7e24859d1d9b19c6b4b91f8797874223cef0c414e3eb7ed1497d58fe6d9a0bf0', 'wood'),
    ('emerald', 838, 846, '43e625ed5bcc596ec2bdbbb3f8c396d5a9a923535bc7acfae09066aedc2335a8', 'stone'),
    ('emerald', 839, 847, 'f12df68a14fe870652a194cd4529016939d8a17d6d4afbf51189e92d9852afd6', 'stone'),
    ('emerald', 660, 668, 'e944b804fade80ddc8b13892d8b979666b4780d978ec70dd563c8e1529ce3e9f', 'stone'),
    ('emerald', 793, 807, '0210c93d6cb63f480a2d633c04a8503c30ea0e0ee5b823d5d2531ddcc94b393a', 'house'),
    ('emerald', 794, 802, 'bc61e9a5e804a96a9a8d8c22e9eedc5bb77c76e870090bde589cc60b7efe4152', 'house'),
]

PC_CAP_CONTRACTS=[
    ('ruby', 'building__pokemon_center', 524, '3fcb36267ba5aa075a133bed7e074953adc6993d4b10e6146e3bbb2fbb93d745', 'clinic_wall'),
    ('ruby', 'building__contest', 589, 'f4fce19afc4abf4aade9dd3607346ade3fc22e4d88dd7dcb6288f83aaf4e9ce8', 'curtain_header'),
    ('ruby', 'building__shop', 605, 'be54ab879fc33cc4e0ece8ea96f00bd1ba22db38e397ad65d8392bdc16d2d111', 'facility_wall'),
    ('ruby', 'building__battle_tower', 640, '11efcf4067d4c211019c13dd898d39c465111d494725d4a4c5435265b2982424', 'facility_wall'),
    ('ruby', 'building__pokemon_day_care', 522, 'be501ccc1a01547ca52b01392367e9f2dcfaf5243d4727564ec11f69db715bf1', 'house_wall'),
    ('ruby', 'building__lab', 622, 'a6d01b33a643e95512677bb2449d7930f97cb1277501cd184030e2cbcccb2199', 'clinic_wall'),
    ('sapphire', 'building__contest', 589, 'f4fce19afc4abf4aade9dd3607346ade3fc22e4d88dd7dcb6288f83aaf4e9ce8', 'curtain_header'),
    ('sapphire', 'building__pokemon_center', 524, '3fcb36267ba5aa075a133bed7e074953adc6993d4b10e6146e3bbb2fbb93d745', 'clinic_wall'),
    ('sapphire', 'building__battle_tower', 640, '11efcf4067d4c211019c13dd898d39c465111d494725d4a4c5435265b2982424', 'facility_wall'),
    ('sapphire', 'building__pokemon_day_care', 522, 'be501ccc1a01547ca52b01392367e9f2dcfaf5243d4727564ec11f69db715bf1', 'house_wall'),
    ('sapphire', 'building__lab', 622, 'a6d01b33a643e95512677bb2449d7930f97cb1277501cd184030e2cbcccb2199', 'clinic_wall'),
    ('sapphire', 'building__shop', 605, 'be54ab879fc33cc4e0ece8ea96f00bd1ba22db38e397ad65d8392bdc16d2d111', 'facility_wall'),
    ('emerald', 'building__pokemon_center', 524, '3fcb36267ba5aa075a133bed7e074953adc6993d4b10e6146e3bbb2fbb93d745', 'clinic_wall'),
    ('emerald', 'building__pokemon_center', 678, 'a6df6beaf7d595cfffd94375f25d53e7527f0d4ade2903909550fa8376e9ecff', 'partition_cap'),
    ('emerald', 'building__battle_frontier', 640, '11efcf4067d4c211019c13dd898d39c465111d494725d4a4c5435265b2982424', 'facility_wall'),
    ('emerald', 'building__contest', 589, 'f4fce19afc4abf4aade9dd3607346ade3fc22e4d88dd7dcb6288f83aaf4e9ce8', 'curtain_header'),
    ('emerald', 'building__battle_arena', 640, '325019d7357c4ed320af4a26b9c5218022b5f2928832a63cb89f52601b873efc', 'wood_wall'),
    ('emerald', 'building__trainer_hill', 814, '39252f18b0551af5a639e263bf24b9575a40a7c1437c7d8fe9b9088d558f51eb', 'counter_return'),
    ('emerald', 'building__lab', 622, 'a6d01b33a643e95512677bb2449d7930f97cb1277501cd184030e2cbcccb2199', 'clinic_wall'),
    ('emerald', 'building__pokemon_day_care', 522, 'be501ccc1a01547ca52b01392367e9f2dcfaf5243d4727564ec11f69db715bf1', 'house_wall'),
    ('emerald', 'building__shop', 605, 'be54ab879fc33cc4e0ece8ea96f00bd1ba22db38e397ad65d8392bdc16d2d111', 'facility_wall'),
    ('emerald', 'building__mossdeep_game_corner', 552, 'ae17f41f298e514eaf14b5124471f1038e97fffdf23b3e97e9e7772f9b84a077', 'wood_wall'),
    ('emerald', 'building__battle_frontier', 760, '71e8f5d51274b77b34a2c1f73cb889c3f700772252bc0d06a5809f85879c4c35', 'facility_wall'),
]

CLINIC_FLOOR_CONTRACTS=[(518, 'fafdcd53504754bd20282c9ec4b7f4393b095c0290d85723c5a73673649b4f10'), (519, 'da8301e3dabbe0df05de58b521f583503216ec19149b3cef90edccc479715189'), (541, 'ea83fb7d02e6943d431b7c126bf9dc4fbdaaa980811f02a2eee0cf6fca4e089d'), (542, '0ddc4805410b13611966c5c3e2152ffefdc815db82517d40428ed830f7ca1f9f'), (544, '1f0ec8d4b43df35f698c870870da61e1e9362fc84bfa30da86b907063a7d6118'), (549, '2218b1091ac4b3f775da2e43aa38c615b8a8a5d891dac19da089ce49f1f0f3a0'), (551, '806d7fb0ca3a1bfd8f094ef3fee44342788ea1d359bb75a9cb35d4b9e4fc86d7'), (553, '8780c7f9de9fe0c87ae2a441fb167fda8b1085e446fc9d5144e103a595f97c82'), (559, 'fad435f2eabb10db7f1c4900cccc4553a48b11d2013b1ab902c2742a55526f18'), (572, '9756bf7cacf33722003b1bf78aea95ff762057d6b81c95ce45d962cad0cffe32'), (580, '05ca07f2be80d125d6f0b23665c76a6f30eae211e2e907161aa0395a3d836246'), (608, '53350e71cb393a36e3a74ab3a9fbaba7ceba4dfac1c5db2316ec604bc34a4c58'), (609, '685c7b12ca5f6ced27e3de60afb74425fd04ca584cdd6c8b310786587c0fc146'), (615, '53350e71cb393a36e3a74ab3a9fbaba7ceba4dfac1c5db2316ec604bc34a4c58'), (628, 'ede038fad59236567e8f1d91b0ace9597cdbaad1c2f95651a22aaf71e12e433e'), (637, 'ae6c8c6d5030f2cc8f0bae167c935e275b3d623dc31b586780468c3ad57f5edf'), (703, '53350e71cb393a36e3a74ab3a9fbaba7ceba4dfac1c5db2316ec604bc34a4c58'), (705, '0ddc4805410b13611966c5c3e2152ffefdc815db82517d40428ed830f7ca1f9f'), (707, '0ddc4805410b13611966c5c3e2152ffefdc815db82517d40428ed830f7ca1f9f'), (708, '0ddc4805410b13611966c5c3e2152ffefdc815db82517d40428ed830f7ca1f9f'), (709, '0ddc4805410b13611966c5c3e2152ffefdc815db82517d40428ed830f7ca1f9f'), (712, '10749da96bc7830a08165f108fa76e52e57a946f7d30655b58b2a4709baae130'), (714, '16e445c12a2857a5f9838fe5ed8e1c3d7afda8f3f9068db76978394285de94da'), (722, 'db9ddd1adcbafd37e55253e89da3b40ac25369607af0b4f1fdb8c86e84f3ee2b'), (729, '9a93ef5c05cbcf022b77e14d48d7b3473de0d0b084a554499f974f1785e8b756')]

TABLE_SOURCE_CONTRACTS=[
    ('ruby', 'large48', [[744, 745, 746], [752, 753, 754]], 'e4850675414d1e8863e98ba7fb76ad5c85e1dc78f25cd58fc441e0ca0d60635b'),
    ('sapphire', 'large48', [[744, 745, 746], [752, 753, 754]], 'e4850675414d1e8863e98ba7fb76ad5c85e1dc78f25cd58fc441e0ca0d60635b'),
    ('emerald', 'large48', [[744, 745, 746], [752, 753, 754]], '1dd263a70895cfc1ee1b50f05dd7948514992b72a0d4d93dfb7e7c2bb556fe8b'),
    ('ruby', 'large64', [[744, 745, 745, 746], [752, 753, 753, 754]], 'ee0233b95be4af162afc6bde1ba604b0006aceaee90982c66ec94773558fb17f'),
    ('sapphire', 'large64', [[744, 745, 745, 746], [752, 753, 753, 754]], 'ee0233b95be4af162afc6bde1ba604b0006aceaee90982c66ec94773558fb17f'),
    ('emerald', 'large64', [[744, 745, 745, 746], [752, 753, 753, 754]], '9e56b780355dc6fa48c329f2aaa58eeb874ec6f75c30e44a2447466223ababc1'),
    ('ruby', 'diningMug', [[584, 585], [592, 593]], 'a0af43d6fa33953c4e9db85ab13f507193c7f18e635c98c33941696ff043533d'),
    ('sapphire', 'diningMug', [[584, 585], [592, 593]], 'a0af43d6fa33953c4e9db85ab13f507193c7f18e635c98c33941696ff043533d'),
    ('emerald', 'diningMug', [[584, 585], [592, 593]], 'bfc3eb625b1c9844b44fd70108f2f1dc9640151ba1bcd0c797bdee0710ffef5b'),
    ('ruby', 'diningPlain', [[584, 606], [592, 593]], '09bf0e4189fd13191901e4bd61fde80dc1be7ff08c09731f6e6a56df3e87236c'),
    ('sapphire', 'diningPlain', [[584, 606], [592, 593]], '09bf0e4189fd13191901e4bd61fde80dc1be7ff08c09731f6e6a56df3e87236c'),
    ('emerald', 'diningPlain', [[584, 606], [592, 593]], '5afc6b8bb25e16c011b2e75b1ca1137ed12a2f5a157baccfa6282949baf69271'),
]

RS_SPECIAL_GYM_CONTRACTS=[
    ('ruby', 'building__rustboro_gym', 516, 'fa5cbb72d7fa2462dd2e7763a529c141d7df3127219a4c4492e9e09fe2f8b01e', 'window'),
    ('ruby', 'building__mauville_gym', 522, 'e25f64616bcc3a107525aeaaf1711dba98b8db7214c1dcd9084466febbd0f0f0', 'compact_statue'),
    ('ruby', 'building__lavaridge_gym', 514, '29d3bcaf43b4f24bbbd229254debe9d98dc2c0b3220f08b2f48cd2bccb64a2ef', 'floor'),
    ('ruby', 'building__lavaridge_gym', 515, '4316d1929cee17d72fa1a294faa9b0af3bf85afe217d4ad62753f8a0fde80f83', 'floor'),
    ('ruby', 'building__lavaridge_gym', 520, '60d7152df892b35455b69b768947ae6ae9b4a16a51ff77b47ae477bedce983ac', 'wall'),
    ('ruby', 'building__lavaridge_gym', 521, '03c222ccde2dc7333aca8f478367a742b21b76ef836fa9d1b5274680f515aaca', 'top_cap'),
    ('ruby', 'building__lavaridge_gym', 529, 'c826d7e744b6d9cd3a483a97adc5f6e19137b845bb74364b82a427e47fe504b7', 'upper_post'),
    ('ruby', 'building__lavaridge_gym', 537, '8de7cfb4d02343119a3b67cc578bd72a63137d41a040a0872c8a5f8ab105a1e0', 'shaft'),
    ('ruby', 'building__lavaridge_gym', 545, 'bda1b343be3881afa00f876af6017fba244e41f9ee9ffeace4e4e2dc06228fd1', 'lower_post'),
    ('ruby', 'building__lavaridge_gym', 553, '3461dbeb70ad32e15bf609ed808aff432a4420d42a6bfa3a23ccc15c2323511e', 'base'),
    ('ruby', 'building__lavaridge_gym', 526, '6c0cc33cbc6ae09588c5e8649daba4afcf75c62f44ecb3b6faaa39db90935df0', 'footer'),
    ('ruby', 'building__lavaridge_gym', 527, 'cb6ee6d95c7deadf0eb141a2b64657c64aaf7055c14fcce4ef52d55b59306611', 'footer'),
    ('sapphire', 'building__rustboro_gym', 516, 'fa5cbb72d7fa2462dd2e7763a529c141d7df3127219a4c4492e9e09fe2f8b01e', 'window'),
    ('sapphire', 'building__mauville_gym', 522, 'e25f64616bcc3a107525aeaaf1711dba98b8db7214c1dcd9084466febbd0f0f0', 'compact_statue'),
    ('sapphire', 'building__lavaridge_gym', 514, '29d3bcaf43b4f24bbbd229254debe9d98dc2c0b3220f08b2f48cd2bccb64a2ef', 'floor'),
    ('sapphire', 'building__lavaridge_gym', 515, '4316d1929cee17d72fa1a294faa9b0af3bf85afe217d4ad62753f8a0fde80f83', 'floor'),
    ('sapphire', 'building__lavaridge_gym', 520, '60d7152df892b35455b69b768947ae6ae9b4a16a51ff77b47ae477bedce983ac', 'wall'),
    ('sapphire', 'building__lavaridge_gym', 521, '03c222ccde2dc7333aca8f478367a742b21b76ef836fa9d1b5274680f515aaca', 'top_cap'),
    ('sapphire', 'building__lavaridge_gym', 529, 'c826d7e744b6d9cd3a483a97adc5f6e19137b845bb74364b82a427e47fe504b7', 'upper_post'),
    ('sapphire', 'building__lavaridge_gym', 537, '8de7cfb4d02343119a3b67cc578bd72a63137d41a040a0872c8a5f8ab105a1e0', 'shaft'),
    ('sapphire', 'building__lavaridge_gym', 545, 'bda1b343be3881afa00f876af6017fba244e41f9ee9ffeace4e4e2dc06228fd1', 'lower_post'),
    ('sapphire', 'building__lavaridge_gym', 553, '3461dbeb70ad32e15bf609ed808aff432a4420d42a6bfa3a23ccc15c2323511e', 'base'),
    ('sapphire', 'building__lavaridge_gym', 526, '6c0cc33cbc6ae09588c5e8649daba4afcf75c62f44ecb3b6faaa39db90935df0', 'footer'),
    ('sapphire', 'building__lavaridge_gym', 527, 'cb6ee6d95c7deadf0eb141a2b64657c64aaf7055c14fcce4ef52d55b59306611', 'footer'),
]

COMPACT_DECOR_SOURCE_CONTRACTS=[
    ('ruby', 'secret_base__secret_base_blue_cave', 'SMALL DESK', 1, 647, 'fc7e571f58e08711bc8b186ef8ffe11582a5758062212695c1348d0f185dd0a4'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'POKéMON DESK', 2, 655, '78c123bc7d3d7ab400563c0883d8276885548d0225d3eed9c6d417ef11788209'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'SMALL CHAIR', 10, 696, '8ea005a1e5835918d921e7e5c2ccd31b84c0a50602e224e79e31b9122152bd06'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'POKéMON CHAIR', 11, 697, '47f2d321ace36e1f01471c23fd79da75d837e04f9dde3f911713507fa123208d'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'HEAVY CHAIR', 12, 698, '44d20dd75c6fb11e393fc77f923a73403f2cfa68070821394274ad3a3bdd29f4'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'PRETTY CHAIR', 13, 704, '2985fff7689debc8722bb81559941332c85b075f081fb6a795eb5a82a2a2576e'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'COMFORT CHAIR', 14, 705, 'afad4ff158ac492c9e107a811b84cf00660433ca6a51a129454e143c0fbb33e4'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'RAGGED CHAIR', 15, 706, '69dcb63332d1f544df751c792fc5803e360e755fc6a97a9b569577600b58c9f1'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'BRICK CHAIR', 16, 712, 'd6dfcf366dbceb127be03482b444c57e2352d821395de516eebcb13fd2354ef5'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'CAMP CHAIR', 17, 713, 'ec18ac59ccd9ecc2f995cd2a26424c740251cb00ec2f1eb0f02fe8d3b3b23cb2'),
    ('ruby', 'secret_base__secret_base_blue_cave', 'HARD CHAIR', 18, 714, 'c4886ee344566158ed07d37a3e1f244c415e1c562536d110b3c118b42cf84ad9'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'SMALL DESK', 1, 647, '94d7d73089ded03d7333a786ac358bdcda0d6ed7e651e6e55b1b5d40b1ca3b59'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'POKéMON DESK', 2, 655, 'c95d95e980a9a25b1499490432dbaab96f343f0010c302b470d05f7b4c577bf9'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'SMALL CHAIR', 10, 696, 'e733572db470d3f1f37e91f7171395910727515612eea6c97fc09e038edb0f13'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'POKéMON CHAIR', 11, 697, 'bedb733a13498f61f581ed5ab4b1ce2eb3761d52309f6aa589d93d3b2e712b15'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'HEAVY CHAIR', 12, 698, '3c4a48b0ef3283dbe0e007189c359e09adf85fa9b8bcfab0a28e8ee258781361'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'PRETTY CHAIR', 13, 704, '0c109846efa2c82b965cc0b11a48328080ff385edfe917adebced69e5b70cb6d'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'COMFORT CHAIR', 14, 705, '720cc4d8ddfdb7b63ded2a577e2d9d51666f6ab14ceaea718c60bbd16ab87f72'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'RAGGED CHAIR', 15, 706, '1d15f1e5921ccee293141c1fb2e3c5e2aa31208fde59f7306777a37784291564'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'BRICK CHAIR', 16, 712, '6aabfc84e165e5c1edf8b6e2f72710ad464fbdefcc9edfd266074a9f02aa9c0a'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'CAMP CHAIR', 17, 713, '19efdbcf64fc3b6bd4c739751509138230848819aa2008c65c8a655e973a06b3'),
    ('ruby', 'secret_base__secret_base_brown_cave', 'HARD CHAIR', 18, 714, '22192a721fa616122ef78786ff2b947575b7cd98f11f67cc61f6af43484903c5'),
    ('ruby', 'secret_base__secret_base_red_cave', 'SMALL DESK', 1, 647, 'b35e86e80008612cf8667ee40b302038cedeec5e12353e2d662826e23c04ae5b'),
    ('ruby', 'secret_base__secret_base_red_cave', 'POKéMON DESK', 2, 655, '49d185dd99c3151d0b9731997ee76000894e3f86439b4abf7e082905d4f6f789'),
    ('ruby', 'secret_base__secret_base_red_cave', 'SMALL CHAIR', 10, 696, 'b43e5307c7cfc4d5523701c4d4eafb57bd7cec7e4bde358e582987d101aaace2'),
    ('ruby', 'secret_base__secret_base_red_cave', 'POKéMON CHAIR', 11, 697, 'fc9371a2e0324367e58470541777efbde978753c7f08be7ab89d633e121ed35e'),
    ('ruby', 'secret_base__secret_base_red_cave', 'HEAVY CHAIR', 12, 698, '706305b56004f9d7f450808541c7f777c15d1057c7a387508471b08e558d2c8c'),
    ('ruby', 'secret_base__secret_base_red_cave', 'PRETTY CHAIR', 13, 704, '64b9eb592704142f1f9bcf0c1f2f14ff6e8c5e120c08269140a4ae7a3e376a2a'),
    ('ruby', 'secret_base__secret_base_red_cave', 'COMFORT CHAIR', 14, 705, 'd4ecb275a48a1074054af5a4962df6c4616642d619565f7952e6ee8c3d01620b'),
    ('ruby', 'secret_base__secret_base_red_cave', 'RAGGED CHAIR', 15, 706, '8fb4d9675ef8bc765fcc7c036cfa01a6e8631dc3ce6186a2c24a54fc0322240f'),
    ('ruby', 'secret_base__secret_base_red_cave', 'BRICK CHAIR', 16, 712, '17658d7cff67e4306978163dd2d0b3afa948356409a3b198060fda430e4e3fdb'),
    ('ruby', 'secret_base__secret_base_red_cave', 'CAMP CHAIR', 17, 713, '16f126d7831a56e536671a3c70dfb577f7ffe25ca3cac94e73d6096b823efc39'),
    ('ruby', 'secret_base__secret_base_red_cave', 'HARD CHAIR', 18, 714, 'dda7d177a567612d28c8b4b776df6383f6088e3d51e6c9a10ddfa3ac786b84c5'),
    ('ruby', 'secret_base__secret_base_shrub', 'SMALL DESK', 1, 647, 'bab67483e481bd383d9762320750410e146f21f3ddf90b089a7af274391b69cc'),
    ('ruby', 'secret_base__secret_base_shrub', 'POKéMON DESK', 2, 655, '7a4b54d2030cb343e5d14901509d85a04011564bcd7ae69d066f137e9aa6d385'),
    ('ruby', 'secret_base__secret_base_shrub', 'SMALL CHAIR', 10, 696, '349c48d878e80ea81b7ca9bbb9b915b0c894b37567e48e96b0fea2e8b18cde8f'),
    ('ruby', 'secret_base__secret_base_shrub', 'POKéMON CHAIR', 11, 697, '2335fa8aa7af426d530bd1a3177d939184c93986cb771565d10419b57a5fe075'),
    ('ruby', 'secret_base__secret_base_shrub', 'HEAVY CHAIR', 12, 698, '8604b37924547c41e1aca0b24af06ca86c4ff3c5ab3f3402265b1ccdb2b006c5'),
    ('ruby', 'secret_base__secret_base_shrub', 'PRETTY CHAIR', 13, 704, 'd84a7f7a254785a0fcd09acebc1ce36a7328655f472be01e8ebe1db9615bb581'),
    ('ruby', 'secret_base__secret_base_shrub', 'COMFORT CHAIR', 14, 705, '295ad19a65521cfec26006c912e7a6e8592cf610cb1cbbee2ef3c5338f6e462a'),
    ('ruby', 'secret_base__secret_base_shrub', 'RAGGED CHAIR', 15, 706, 'c51153f77b110b0f022fd388d817f2f41410746c822969bbeceb542f8666cf8b'),
    ('ruby', 'secret_base__secret_base_shrub', 'BRICK CHAIR', 16, 712, 'b2649b916ba47a2788eed31db94e8cfa019084845b30a65822ba35d6da55541b'),
    ('ruby', 'secret_base__secret_base_shrub', 'CAMP CHAIR', 17, 713, '325b859ecee807d72b9957bddd1edeef72a0d6347ea02ca576df7d17b8a15824'),
    ('ruby', 'secret_base__secret_base_shrub', 'HARD CHAIR', 18, 714, 'c836c535751bcebb559d3440566a16beaf59fb4404c0414a8e27b326d269092e'),
    ('ruby', 'secret_base__secret_base_tree', 'SMALL DESK', 1, 647, '9ed90708333a935aaa2029c709cc5976f730d3d55bcdc488ce2e0323f08c2f3a'),
    ('ruby', 'secret_base__secret_base_tree', 'POKéMON DESK', 2, 655, '2a3c3a9769dc47eef328e834af8d776002c1e64d46285d3bc190c1d2e91d1d79'),
    ('ruby', 'secret_base__secret_base_tree', 'SMALL CHAIR', 10, 696, '41f924a18c9a179b630d6f1adc61c76bdb80ae665327a47cb47e017b34dc57fd'),
    ('ruby', 'secret_base__secret_base_tree', 'POKéMON CHAIR', 11, 697, '2a175f0c9e11a62eb720ade0f3d184a334bdc7d23fece2589c549c186c1b6de6'),
    ('ruby', 'secret_base__secret_base_tree', 'HEAVY CHAIR', 12, 698, 'b5bb62777ed2050d9f5704f92c41215f228cdf2b9d62195e9de3b46b4b65847e'),
    ('ruby', 'secret_base__secret_base_tree', 'PRETTY CHAIR', 13, 704, '5a2b23ab3895a5a76dd27a19d3fc1cc4761633ebb325ec66c797ae0eed2b0d3a'),
    ('ruby', 'secret_base__secret_base_tree', 'COMFORT CHAIR', 14, 705, '4a31bbe9984e88023f5cbcf242619a0c368bf792765b62c14b87bd650e191b46'),
    ('ruby', 'secret_base__secret_base_tree', 'RAGGED CHAIR', 15, 706, 'b8d75fdef0fc035eaa54ccfaab2aa61093575da2887b8168c43ec86d79c28d48'),
    ('ruby', 'secret_base__secret_base_tree', 'BRICK CHAIR', 16, 712, '4d6a3b2808986a6f2f61a2fd9f30a34a205970d29d1f3f7b928be10c7f6f8c98'),
    ('ruby', 'secret_base__secret_base_tree', 'CAMP CHAIR', 17, 713, '42d7854cce0a0bab03288ed4548cf94459086254e92c1c09dcd9094b72faa1d0'),
    ('ruby', 'secret_base__secret_base_tree', 'HARD CHAIR', 18, 714, '8388d1a891bf975037b5aff5c7f44226dc20c054aeafb4187998c91d2945cc9c'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'SMALL DESK', 1, 647, '932a6ca519b2020b388387dafafb6e7db362776a4fedca33de478280a62888b0'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'POKéMON DESK', 2, 655, '0987eaf6df5ba7aeaea27685802f2222f1cbc686ace5de3fbfe80e05f23a0e72'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'SMALL CHAIR', 10, 696, 'f0cb9535c3cbe17b45d8ff9c098109f3748571c360ee86ae3754723b7244b2e1'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'POKéMON CHAIR', 11, 697, 'dba25a47f2b0019a1ce999d3a4d6e6993ae16337d2462d29906a264ac9ddbcb1'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'HEAVY CHAIR', 12, 698, 'cbaeebef0b4604d777dea944e6fa5e0dfa1ba49f84808bfe25ec52257a1e9458'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'PRETTY CHAIR', 13, 704, '0322d3c6252eaeaebed16bbcd3621199a8991957bae42d4b336dfe9b8da1d49a'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'COMFORT CHAIR', 14, 705, '21981473c56923945eba254207a3b8f51e8b4fd73c71048858ba539da7d1536e'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'RAGGED CHAIR', 15, 706, 'c385ee2e7eb4fb0e37fdcbea125607b08a75c390e6a5d0e233d748eb120c9669'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'BRICK CHAIR', 16, 712, 'e8b132e5fae4a66973a10aad3b116b5d3ac221efa3127fc410067239e99146fb'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'CAMP CHAIR', 17, 713, '2abde0e17ca2f22a2961e2d3b7b7cac796c638d91427ef2e02b65032a7b82507'),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'HARD CHAIR', 18, 714, 'f67193f26684980ed6e6cb67a55006d896ec9e899022871a87f3374ac85d6791'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'SMALL DESK', 1, 647, 'fc7e571f58e08711bc8b186ef8ffe11582a5758062212695c1348d0f185dd0a4'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'POKéMON DESK', 2, 655, '78c123bc7d3d7ab400563c0883d8276885548d0225d3eed9c6d417ef11788209'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'SMALL CHAIR', 10, 696, '8ea005a1e5835918d921e7e5c2ccd31b84c0a50602e224e79e31b9122152bd06'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'POKéMON CHAIR', 11, 697, '47f2d321ace36e1f01471c23fd79da75d837e04f9dde3f911713507fa123208d'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'HEAVY CHAIR', 12, 698, '44d20dd75c6fb11e393fc77f923a73403f2cfa68070821394274ad3a3bdd29f4'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'PRETTY CHAIR', 13, 704, '2985fff7689debc8722bb81559941332c85b075f081fb6a795eb5a82a2a2576e'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'COMFORT CHAIR', 14, 705, 'afad4ff158ac492c9e107a811b84cf00660433ca6a51a129454e143c0fbb33e4'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'RAGGED CHAIR', 15, 706, '69dcb63332d1f544df751c792fc5803e360e755fc6a97a9b569577600b58c9f1'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'BRICK CHAIR', 16, 712, 'd6dfcf366dbceb127be03482b444c57e2352d821395de516eebcb13fd2354ef5'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'CAMP CHAIR', 17, 713, 'ec18ac59ccd9ecc2f995cd2a26424c740251cb00ec2f1eb0f02fe8d3b3b23cb2'),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'HARD CHAIR', 18, 714, 'c4886ee344566158ed07d37a3e1f244c415e1c562536d110b3c118b42cf84ad9'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'SMALL DESK', 1, 647, '94d7d73089ded03d7333a786ac358bdcda0d6ed7e651e6e55b1b5d40b1ca3b59'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'POKéMON DESK', 2, 655, 'c95d95e980a9a25b1499490432dbaab96f343f0010c302b470d05f7b4c577bf9'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'SMALL CHAIR', 10, 696, 'e733572db470d3f1f37e91f7171395910727515612eea6c97fc09e038edb0f13'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'POKéMON CHAIR', 11, 697, 'bedb733a13498f61f581ed5ab4b1ce2eb3761d52309f6aa589d93d3b2e712b15'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'HEAVY CHAIR', 12, 698, '3c4a48b0ef3283dbe0e007189c359e09adf85fa9b8bcfab0a28e8ee258781361'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'PRETTY CHAIR', 13, 704, '0c109846efa2c82b965cc0b11a48328080ff385edfe917adebced69e5b70cb6d'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'COMFORT CHAIR', 14, 705, '720cc4d8ddfdb7b63ded2a577e2d9d51666f6ab14ceaea718c60bbd16ab87f72'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'RAGGED CHAIR', 15, 706, '1d15f1e5921ccee293141c1fb2e3c5e2aa31208fde59f7306777a37784291564'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'BRICK CHAIR', 16, 712, '6aabfc84e165e5c1edf8b6e2f72710ad464fbdefcc9edfd266074a9f02aa9c0a'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'CAMP CHAIR', 17, 713, '19efdbcf64fc3b6bd4c739751509138230848819aa2008c65c8a655e973a06b3'),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'HARD CHAIR', 18, 714, '22192a721fa616122ef78786ff2b947575b7cd98f11f67cc61f6af43484903c5'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'SMALL DESK', 1, 647, 'b35e86e80008612cf8667ee40b302038cedeec5e12353e2d662826e23c04ae5b'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'POKéMON DESK', 2, 655, '49d185dd99c3151d0b9731997ee76000894e3f86439b4abf7e082905d4f6f789'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'SMALL CHAIR', 10, 696, 'b43e5307c7cfc4d5523701c4d4eafb57bd7cec7e4bde358e582987d101aaace2'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'POKéMON CHAIR', 11, 697, 'fc9371a2e0324367e58470541777efbde978753c7f08be7ab89d633e121ed35e'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'HEAVY CHAIR', 12, 698, '706305b56004f9d7f450808541c7f777c15d1057c7a387508471b08e558d2c8c'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'PRETTY CHAIR', 13, 704, '64b9eb592704142f1f9bcf0c1f2f14ff6e8c5e120c08269140a4ae7a3e376a2a'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'COMFORT CHAIR', 14, 705, 'd4ecb275a48a1074054af5a4962df6c4616642d619565f7952e6ee8c3d01620b'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'RAGGED CHAIR', 15, 706, '8fb4d9675ef8bc765fcc7c036cfa01a6e8631dc3ce6186a2c24a54fc0322240f'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'BRICK CHAIR', 16, 712, '17658d7cff67e4306978163dd2d0b3afa948356409a3b198060fda430e4e3fdb'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'CAMP CHAIR', 17, 713, '16f126d7831a56e536671a3c70dfb577f7ffe25ca3cac94e73d6096b823efc39'),
    ('sapphire', 'secret_base__secret_base_red_cave', 'HARD CHAIR', 18, 714, 'dda7d177a567612d28c8b4b776df6383f6088e3d51e6c9a10ddfa3ac786b84c5'),
    ('sapphire', 'secret_base__secret_base_shrub', 'SMALL DESK', 1, 647, 'bab67483e481bd383d9762320750410e146f21f3ddf90b089a7af274391b69cc'),
    ('sapphire', 'secret_base__secret_base_shrub', 'POKéMON DESK', 2, 655, '7a4b54d2030cb343e5d14901509d85a04011564bcd7ae69d066f137e9aa6d385'),
    ('sapphire', 'secret_base__secret_base_shrub', 'SMALL CHAIR', 10, 696, '349c48d878e80ea81b7ca9bbb9b915b0c894b37567e48e96b0fea2e8b18cde8f'),
    ('sapphire', 'secret_base__secret_base_shrub', 'POKéMON CHAIR', 11, 697, '2335fa8aa7af426d530bd1a3177d939184c93986cb771565d10419b57a5fe075'),
    ('sapphire', 'secret_base__secret_base_shrub', 'HEAVY CHAIR', 12, 698, '8604b37924547c41e1aca0b24af06ca86c4ff3c5ab3f3402265b1ccdb2b006c5'),
    ('sapphire', 'secret_base__secret_base_shrub', 'PRETTY CHAIR', 13, 704, 'd84a7f7a254785a0fcd09acebc1ce36a7328655f472be01e8ebe1db9615bb581'),
    ('sapphire', 'secret_base__secret_base_shrub', 'COMFORT CHAIR', 14, 705, '295ad19a65521cfec26006c912e7a6e8592cf610cb1cbbee2ef3c5338f6e462a'),
    ('sapphire', 'secret_base__secret_base_shrub', 'RAGGED CHAIR', 15, 706, 'c51153f77b110b0f022fd388d817f2f41410746c822969bbeceb542f8666cf8b'),
    ('sapphire', 'secret_base__secret_base_shrub', 'BRICK CHAIR', 16, 712, 'b2649b916ba47a2788eed31db94e8cfa019084845b30a65822ba35d6da55541b'),
    ('sapphire', 'secret_base__secret_base_shrub', 'CAMP CHAIR', 17, 713, '325b859ecee807d72b9957bddd1edeef72a0d6347ea02ca576df7d17b8a15824'),
    ('sapphire', 'secret_base__secret_base_shrub', 'HARD CHAIR', 18, 714, 'c836c535751bcebb559d3440566a16beaf59fb4404c0414a8e27b326d269092e'),
    ('sapphire', 'secret_base__secret_base_tree', 'SMALL DESK', 1, 647, '9ed90708333a935aaa2029c709cc5976f730d3d55bcdc488ce2e0323f08c2f3a'),
    ('sapphire', 'secret_base__secret_base_tree', 'POKéMON DESK', 2, 655, '2a3c3a9769dc47eef328e834af8d776002c1e64d46285d3bc190c1d2e91d1d79'),
    ('sapphire', 'secret_base__secret_base_tree', 'SMALL CHAIR', 10, 696, '41f924a18c9a179b630d6f1adc61c76bdb80ae665327a47cb47e017b34dc57fd'),
    ('sapphire', 'secret_base__secret_base_tree', 'POKéMON CHAIR', 11, 697, '2a175f0c9e11a62eb720ade0f3d184a334bdc7d23fece2589c549c186c1b6de6'),
    ('sapphire', 'secret_base__secret_base_tree', 'HEAVY CHAIR', 12, 698, 'b5bb62777ed2050d9f5704f92c41215f228cdf2b9d62195e9de3b46b4b65847e'),
    ('sapphire', 'secret_base__secret_base_tree', 'PRETTY CHAIR', 13, 704, '5a2b23ab3895a5a76dd27a19d3fc1cc4761633ebb325ec66c797ae0eed2b0d3a'),
    ('sapphire', 'secret_base__secret_base_tree', 'COMFORT CHAIR', 14, 705, '4a31bbe9984e88023f5cbcf242619a0c368bf792765b62c14b87bd650e191b46'),
    ('sapphire', 'secret_base__secret_base_tree', 'RAGGED CHAIR', 15, 706, 'b8d75fdef0fc035eaa54ccfaab2aa61093575da2887b8168c43ec86d79c28d48'),
    ('sapphire', 'secret_base__secret_base_tree', 'BRICK CHAIR', 16, 712, '4d6a3b2808986a6f2f61a2fd9f30a34a205970d29d1f3f7b928be10c7f6f8c98'),
    ('sapphire', 'secret_base__secret_base_tree', 'CAMP CHAIR', 17, 713, '42d7854cce0a0bab03288ed4548cf94459086254e92c1c09dcd9094b72faa1d0'),
    ('sapphire', 'secret_base__secret_base_tree', 'HARD CHAIR', 18, 714, '8388d1a891bf975037b5aff5c7f44226dc20c054aeafb4187998c91d2945cc9c'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'SMALL DESK', 1, 647, '932a6ca519b2020b388387dafafb6e7db362776a4fedca33de478280a62888b0'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'POKéMON DESK', 2, 655, '0987eaf6df5ba7aeaea27685802f2222f1cbc686ace5de3fbfe80e05f23a0e72'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'SMALL CHAIR', 10, 696, 'f0cb9535c3cbe17b45d8ff9c098109f3748571c360ee86ae3754723b7244b2e1'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'POKéMON CHAIR', 11, 697, 'dba25a47f2b0019a1ce999d3a4d6e6993ae16337d2462d29906a264ac9ddbcb1'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'HEAVY CHAIR', 12, 698, 'cbaeebef0b4604d777dea944e6fa5e0dfa1ba49f84808bfe25ec52257a1e9458'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'PRETTY CHAIR', 13, 704, '0322d3c6252eaeaebed16bbcd3621199a8991957bae42d4b336dfe9b8da1d49a'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'COMFORT CHAIR', 14, 705, '21981473c56923945eba254207a3b8f51e8b4fd73c71048858ba539da7d1536e'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'RAGGED CHAIR', 15, 706, 'c385ee2e7eb4fb0e37fdcbea125607b08a75c390e6a5d0e233d748eb120c9669'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'BRICK CHAIR', 16, 712, 'e8b132e5fae4a66973a10aad3b116b5d3ac221efa3127fc410067239e99146fb'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'CAMP CHAIR', 17, 713, '2abde0e17ca2f22a2961e2d3b7b7cac796c638d91427ef2e02b65032a7b82507'),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'HARD CHAIR', 18, 714, 'f67193f26684980ed6e6cb67a55006d896ec9e899022871a87f3374ac85d6791'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'SMALL DESK', 1, 647, 'fc7e571f58e08711bc8b186ef8ffe11582a5758062212695c1348d0f185dd0a4'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'POKéMON DESK', 2, 655, '78c123bc7d3d7ab400563c0883d8276885548d0225d3eed9c6d417ef11788209'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'SMALL CHAIR', 10, 696, '8ea005a1e5835918d921e7e5c2ccd31b84c0a50602e224e79e31b9122152bd06'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'POKéMON CHAIR', 11, 697, '47f2d321ace36e1f01471c23fd79da75d837e04f9dde3f911713507fa123208d'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'HEAVY CHAIR', 12, 698, '44d20dd75c6fb11e393fc77f923a73403f2cfa68070821394274ad3a3bdd29f4'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'PRETTY CHAIR', 13, 704, '2985fff7689debc8722bb81559941332c85b075f081fb6a795eb5a82a2a2576e'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'COMFORT CHAIR', 14, 705, 'afad4ff158ac492c9e107a811b84cf00660433ca6a51a129454e143c0fbb33e4'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'RAGGED CHAIR', 15, 706, '69dcb63332d1f544df751c792fc5803e360e755fc6a97a9b569577600b58c9f1'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'BRICK CHAIR', 16, 712, 'd6dfcf366dbceb127be03482b444c57e2352d821395de516eebcb13fd2354ef5'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'CAMP CHAIR', 17, 713, 'ec18ac59ccd9ecc2f995cd2a26424c740251cb00ec2f1eb0f02fe8d3b3b23cb2'),
    ('emerald', 'secret_base__secret_base_blue_cave', 'HARD CHAIR', 18, 714, 'c4886ee344566158ed07d37a3e1f244c415e1c562536d110b3c118b42cf84ad9'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'SMALL DESK', 1, 647, '94d7d73089ded03d7333a786ac358bdcda0d6ed7e651e6e55b1b5d40b1ca3b59'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'POKéMON DESK', 2, 655, 'c95d95e980a9a25b1499490432dbaab96f343f0010c302b470d05f7b4c577bf9'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'SMALL CHAIR', 10, 696, 'e733572db470d3f1f37e91f7171395910727515612eea6c97fc09e038edb0f13'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'POKéMON CHAIR', 11, 697, 'bedb733a13498f61f581ed5ab4b1ce2eb3761d52309f6aa589d93d3b2e712b15'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'HEAVY CHAIR', 12, 698, '3c4a48b0ef3283dbe0e007189c359e09adf85fa9b8bcfab0a28e8ee258781361'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'PRETTY CHAIR', 13, 704, '0c109846efa2c82b965cc0b11a48328080ff385edfe917adebced69e5b70cb6d'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'COMFORT CHAIR', 14, 705, '720cc4d8ddfdb7b63ded2a577e2d9d51666f6ab14ceaea718c60bbd16ab87f72'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'RAGGED CHAIR', 15, 706, '1d15f1e5921ccee293141c1fb2e3c5e2aa31208fde59f7306777a37784291564'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'BRICK CHAIR', 16, 712, '6aabfc84e165e5c1edf8b6e2f72710ad464fbdefcc9edfd266074a9f02aa9c0a'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'CAMP CHAIR', 17, 713, '19efdbcf64fc3b6bd4c739751509138230848819aa2008c65c8a655e973a06b3'),
    ('emerald', 'secret_base__secret_base_brown_cave', 'HARD CHAIR', 18, 714, '22192a721fa616122ef78786ff2b947575b7cd98f11f67cc61f6af43484903c5'),
    ('emerald', 'secret_base__secret_base_red_cave', 'SMALL DESK', 1, 647, 'b35e86e80008612cf8667ee40b302038cedeec5e12353e2d662826e23c04ae5b'),
    ('emerald', 'secret_base__secret_base_red_cave', 'POKéMON DESK', 2, 655, '49d185dd99c3151d0b9731997ee76000894e3f86439b4abf7e082905d4f6f789'),
    ('emerald', 'secret_base__secret_base_red_cave', 'SMALL CHAIR', 10, 696, 'b43e5307c7cfc4d5523701c4d4eafb57bd7cec7e4bde358e582987d101aaace2'),
    ('emerald', 'secret_base__secret_base_red_cave', 'POKéMON CHAIR', 11, 697, 'fc9371a2e0324367e58470541777efbde978753c7f08be7ab89d633e121ed35e'),
    ('emerald', 'secret_base__secret_base_red_cave', 'HEAVY CHAIR', 12, 698, '706305b56004f9d7f450808541c7f777c15d1057c7a387508471b08e558d2c8c'),
    ('emerald', 'secret_base__secret_base_red_cave', 'PRETTY CHAIR', 13, 704, '64b9eb592704142f1f9bcf0c1f2f14ff6e8c5e120c08269140a4ae7a3e376a2a'),
    ('emerald', 'secret_base__secret_base_red_cave', 'COMFORT CHAIR', 14, 705, 'd4ecb275a48a1074054af5a4962df6c4616642d619565f7952e6ee8c3d01620b'),
    ('emerald', 'secret_base__secret_base_red_cave', 'RAGGED CHAIR', 15, 706, '8fb4d9675ef8bc765fcc7c036cfa01a6e8631dc3ce6186a2c24a54fc0322240f'),
    ('emerald', 'secret_base__secret_base_red_cave', 'BRICK CHAIR', 16, 712, '17658d7cff67e4306978163dd2d0b3afa948356409a3b198060fda430e4e3fdb'),
    ('emerald', 'secret_base__secret_base_red_cave', 'CAMP CHAIR', 17, 713, '16f126d7831a56e536671a3c70dfb577f7ffe25ca3cac94e73d6096b823efc39'),
    ('emerald', 'secret_base__secret_base_red_cave', 'HARD CHAIR', 18, 714, 'dda7d177a567612d28c8b4b776df6383f6088e3d51e6c9a10ddfa3ac786b84c5'),
    ('emerald', 'secret_base__secret_base_shrub', 'SMALL DESK', 1, 647, 'bab67483e481bd383d9762320750410e146f21f3ddf90b089a7af274391b69cc'),
    ('emerald', 'secret_base__secret_base_shrub', 'POKéMON DESK', 2, 655, '7a4b54d2030cb343e5d14901509d85a04011564bcd7ae69d066f137e9aa6d385'),
    ('emerald', 'secret_base__secret_base_shrub', 'SMALL CHAIR', 10, 696, '349c48d878e80ea81b7ca9bbb9b915b0c894b37567e48e96b0fea2e8b18cde8f'),
    ('emerald', 'secret_base__secret_base_shrub', 'POKéMON CHAIR', 11, 697, '2335fa8aa7af426d530bd1a3177d939184c93986cb771565d10419b57a5fe075'),
    ('emerald', 'secret_base__secret_base_shrub', 'HEAVY CHAIR', 12, 698, '8604b37924547c41e1aca0b24af06ca86c4ff3c5ab3f3402265b1ccdb2b006c5'),
    ('emerald', 'secret_base__secret_base_shrub', 'PRETTY CHAIR', 13, 704, 'd84a7f7a254785a0fcd09acebc1ce36a7328655f472be01e8ebe1db9615bb581'),
    ('emerald', 'secret_base__secret_base_shrub', 'COMFORT CHAIR', 14, 705, '295ad19a65521cfec26006c912e7a6e8592cf610cb1cbbee2ef3c5338f6e462a'),
    ('emerald', 'secret_base__secret_base_shrub', 'RAGGED CHAIR', 15, 706, 'c51153f77b110b0f022fd388d817f2f41410746c822969bbeceb542f8666cf8b'),
    ('emerald', 'secret_base__secret_base_shrub', 'BRICK CHAIR', 16, 712, 'b2649b916ba47a2788eed31db94e8cfa019084845b30a65822ba35d6da55541b'),
    ('emerald', 'secret_base__secret_base_shrub', 'CAMP CHAIR', 17, 713, '325b859ecee807d72b9957bddd1edeef72a0d6347ea02ca576df7d17b8a15824'),
    ('emerald', 'secret_base__secret_base_shrub', 'HARD CHAIR', 18, 714, 'c836c535751bcebb559d3440566a16beaf59fb4404c0414a8e27b326d269092e'),
    ('emerald', 'secret_base__secret_base_tree', 'SMALL DESK', 1, 647, '9ed90708333a935aaa2029c709cc5976f730d3d55bcdc488ce2e0323f08c2f3a'),
    ('emerald', 'secret_base__secret_base_tree', 'POKéMON DESK', 2, 655, '2a3c3a9769dc47eef328e834af8d776002c1e64d46285d3bc190c1d2e91d1d79'),
    ('emerald', 'secret_base__secret_base_tree', 'SMALL CHAIR', 10, 696, '41f924a18c9a179b630d6f1adc61c76bdb80ae665327a47cb47e017b34dc57fd'),
    ('emerald', 'secret_base__secret_base_tree', 'POKéMON CHAIR', 11, 697, '2a175f0c9e11a62eb720ade0f3d184a334bdc7d23fece2589c549c186c1b6de6'),
    ('emerald', 'secret_base__secret_base_tree', 'HEAVY CHAIR', 12, 698, 'b5bb62777ed2050d9f5704f92c41215f228cdf2b9d62195e9de3b46b4b65847e'),
    ('emerald', 'secret_base__secret_base_tree', 'PRETTY CHAIR', 13, 704, '5a2b23ab3895a5a76dd27a19d3fc1cc4761633ebb325ec66c797ae0eed2b0d3a'),
    ('emerald', 'secret_base__secret_base_tree', 'COMFORT CHAIR', 14, 705, '4a31bbe9984e88023f5cbcf242619a0c368bf792765b62c14b87bd650e191b46'),
    ('emerald', 'secret_base__secret_base_tree', 'RAGGED CHAIR', 15, 706, 'b8d75fdef0fc035eaa54ccfaab2aa61093575da2887b8168c43ec86d79c28d48'),
    ('emerald', 'secret_base__secret_base_tree', 'BRICK CHAIR', 16, 712, '4d6a3b2808986a6f2f61a2fd9f30a34a205970d29d1f3f7b928be10c7f6f8c98'),
    ('emerald', 'secret_base__secret_base_tree', 'CAMP CHAIR', 17, 713, '42d7854cce0a0bab03288ed4548cf94459086254e92c1c09dcd9094b72faa1d0'),
    ('emerald', 'secret_base__secret_base_tree', 'HARD CHAIR', 18, 714, '8388d1a891bf975037b5aff5c7f44226dc20c054aeafb4187998c91d2945cc9c'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'SMALL DESK', 1, 647, '932a6ca519b2020b388387dafafb6e7db362776a4fedca33de478280a62888b0'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'POKéMON DESK', 2, 655, '0987eaf6df5ba7aeaea27685802f2222f1cbc686ace5de3fbfe80e05f23a0e72'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'SMALL CHAIR', 10, 696, 'f0cb9535c3cbe17b45d8ff9c098109f3748571c360ee86ae3754723b7244b2e1'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'POKéMON CHAIR', 11, 697, 'dba25a47f2b0019a1ce999d3a4d6e6993ae16337d2462d29906a264ac9ddbcb1'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'HEAVY CHAIR', 12, 698, 'cbaeebef0b4604d777dea944e6fa5e0dfa1ba49f84808bfe25ec52257a1e9458'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'PRETTY CHAIR', 13, 704, '0322d3c6252eaeaebed16bbcd3621199a8991957bae42d4b336dfe9b8da1d49a'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'COMFORT CHAIR', 14, 705, '21981473c56923945eba254207a3b8f51e8b4fd73c71048858ba539da7d1536e'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'RAGGED CHAIR', 15, 706, 'c385ee2e7eb4fb0e37fdcbea125607b08a75c390e6a5d0e233d748eb120c9669'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'BRICK CHAIR', 16, 712, 'e8b132e5fae4a66973a10aad3b116b5d3ac221efa3127fc410067239e99146fb'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'CAMP CHAIR', 17, 713, '2abde0e17ca2f22a2961e2d3b7b7cac796c638d91427ef2e02b65032a7b82507'),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'HARD CHAIR', 18, 714, 'f67193f26684980ed6e6cb67a55006d896ec9e899022871a87f3374ac85d6791'),
]

CONTEXT_SURFACE_CONTRACTS=[
    ('general__bike_shop', 559, '5b253c51fe6d3be9820600d3b96e39e69b4384bc2cc2c3d4769325df99b18d0d', 'stone'),
    ('building__generic_building', 1023, '723a11ffcda737acec2e0927bedcc1f907e1043745482105a73c80c0d81e9658', 'stone'),
    ('general__contest', 533, 'd115441d3fd3105a975f7b8f8870f97f4d20d33713ca93cafe00249782eb7905', 'facility'),
    ('general__facility', 946, '1067680bfc3e70719f8240c46cd42e60bbb5896e51cb9301b2225be9cbc56e12', 'wall_facility'),
    ('building__lilycove_museum', 616, 'daa7ecc1c0566479d1e864c7035d016bc10aa0f626d168ff2e53018b1f3c02a2', 'stone'),
    ('building__elite_four', 721, '4139716c47ed1b131e52bb344b522f0921c7a40864cfed74c384735299518fe8', 'blue_tile'),
    ('building__elite_four', 720, '018461ff302966724664aa668791c4ac00010f8bbda37209080e68653454b4f2', 'blue_tile'),
    ('building__mossdeep_game_corner', 522, '3eeea9e49d9daae36ac241f0abf260f6ab544e53fbaac22ff25b204d3b3ba849', 'wood'),
    ('building__lilycove_museum', 617, '5874816a790419007550efe7e172b7932f193ad8e6f095c9e8046b70a630dc31', 'stone'),
    ('general__inside_ship', 713, '2b0cbfaf044b2f165585e09a27b4be3cfbe8e48c64e8f21c443e83357e8e0f46', 'ship'),
    ('building__trainer_hill', 569, 'd39d566808c89d62d65ea380a3ac749230a58f29c6db029123cce29fb8a41527', 'tatami'),
    ('building__battle_factory', 514, 'a97680bfa252b11c9c7de6579af8bdd5b333fb97999a7b5ecc8a364519d7ddea', 'facility'),
    ('general__inside_ship', 515, '893862911aeaed304af23baedf8032f4921d00157b47faaacba5266421fb00b4', 'ship'),
    ('building__battle_frontier_ranking_hall', 515, '487023428d63cd714f3380b3a113ab6880970f680e8fc8906cee9e0d8b373e83', 'stone'),
    ('general__facility', 516, '2ffff7a46bd2af82021030d2ba54d0f5e644378549f9ea213b3667c85b828b7f', 'stone'),
    ('building__contest', 559, 'd2e5274410dd24d141704f6b15d494439d2979b41700f0b4eedb7b15dc15f648', 'wall_facility'),
    ('building__battle_frontier_ranking_hall', 523, 'bed6cdde10c23ca112dbd832feaf88b5612db5f23dc28012af2fdc9ddbd57979', 'stone'),
    ('general__inside_ship', 525, '58def2058e08f85a4cec104b88ff1527071ae619440689bf01202764afd80f5f', 'ship'),
    ('general__battle_palace', 513, '805323d4330c91412e0e3b27fd463697daae31c9d04fabe31ff4befa16148e30', 'house'),
    ('general__facility', 515, '3a1ba707ecaf17ab94e59b032db13a6d8cc31f73800ec13e2db360e777b0030f', 'stone'),
    ('building__battle_pike', 706, 'f812de7221ef833b6473963994dc3563ab68fd796ea48c42a63bfba34e4459bb', 'casino'),
    ('building__lab', 607, 'e8fd1a0a4ec2d13f140054d115a1dae6fbd273b228aac0c89d25486a0108d02c', 'wall_facility'),
    ('building__cable_club', 597, '071070c6110e8d2a0c7c0ee2a187e12a9410abfb0fdd297227c33be6c4bf2427', 'link'),
    ('general__inside_ship', 698, '2b0cbfaf044b2f165585e09a27b4be3cfbe8e48c64e8f21c443e83357e8e0f46', 'ship'),
    ('building__petalburg_gym', 521, 'bfc8c5dc6d5037e706ca3d455083dc3c28e309358f5842a4e015069e2f83b1e4', 'wood'),
    ('general__facility', 889, 'e111d4a04f07f3956f1fc2ae2fc913ac671cb69a33874da1e0c531cbb0e743a6', 'wall_facility'),
    ('building__battle_dome', 834, 'cfe3e09038504b1df37b43b352bb1e72d7f82a59446fc45146c3f32b60f72435', 'facility'),
    ('building__battle_pyramid', 627, 'd1d1056302d2e359870f03e1dc6f972d3ac87c2d4028c0c371c4fed46392b2b2', 'ruins'),
    ('building__contest', 525, '16dc2b59a4603489af68d56a001233360c0a4809f7518ddc20bfa1379fe92b10', 'wall_facility'),
    ('building__generic_building', 1008, 'e27c3a93140b6bc53747351c534c678a0af61661102465f66fcb48ae83f42d78', 'wall_house'),
    ('building__elite_four', 527, '3752867c9059e21f3f8cf17ca0c172748508266b3874d64db005e63e0492aa73', 'wall_facility'),
    ('building__elite_four', 519, '06818affd452951c03ed5d5e7d8cd698ecc3e410e31e611eaffcb98ceb168f74', 'wall_facility'),
    ('building__shop', 749, 'eb0e95a1f8b2b6f7900a7814cb7852d6538fa095fca909dafc1c5c53c03aed41', 'mart'),
    ('building__battle_dome', 777, '8ba3767acad4bc51e68cb4cd03fb1376eba8944e75d4621388fa4068c5c66dc4', 'tatami'),
    ('building__battle_pike', 730, '735e5b375380d4c69eabc9f52355211ccdf8fac3af2924fff7569e7ea58c6c00', 'house'),
    ('building__trick_house_puzzle', 548, 'a97ac8fb8e18d212a4b1490e537f3b40f2763052607ae0b32b492adcfa676126', 'wall_house'),
    ('building__shop', 586, '12eccb76ebfdcbae12fee3f66de6ac9c76bee222d9235e85bc71c4187cdc2de8', 'mart'),
    ('building__lavaridge_gym', 514, '55084297f1ef45c895f9d4a8b5bf7120509e3dbcb6a190f5cbdfab32a2bcb24a', 'ruins'),
    ('general__inside_ship', 570, 'd204fcb996523d9a322efb275b4fb5b3a8c95c179d1f94d0cafd9eed308b1f63', 'ship'),
    ('building__battle_pyramid', 613, '5ff6358dd4af899b8ae3a63bf80ba32eefb1f147a31eb067a6c4b6869bd6ee34', 'ruins'),
    ('building__trick_house_puzzle', 625, '62e343e68f856e3c00e223ae5616379db2adb52deb0e1f074b23b9c44d31431f', 'tatami'),
    ('general__facility', 870, '0c6d4acd834275df9ab0deeeac906257f437494b95d88650c295679efcdaefbb', 'stone'),
    ('building__battle_pyramid', 609, '45ae7a1f263c511ed24ffe48cdb356e9a6f915cc62abdfde3b4f61cbda1c84d7', 'ruins'),
    ('building__contest', 552, '02145b0c3850c355a8d32aa19891331b7d2490c0b0e4bea0761c629514edd035', 'facility'),
    ('building__contest', 614, 'eb8de25edc7e89be7ffe9af659bf9be71cb920c63186327f762792ebce1a080b', 'facility'),
    ('building__contest', 554, '94bc9a6a6e04a1b05c564fb0abd4d9e65c5c335e359939857d92a8e0742f5764', 'facility'),
    ('general__facility', 669, '132e278fc5123d96c22b3efbd3dbb4d5f8499af74082c7fc81189ef2772ef5c4', 'facility'),
    ('building__elite_four', 732, 'd60c61d0fbcd7ef708d588762be9a402dc7356ba01afd6d1b38432f41767c4b1', 'blue_tile'),
    ('building__elite_four', 740, '95602a44a27585cd1a0c6e20547185e53bc1731a440ad0b8ae0fa9c5e4a43f08', 'blue_tile'),
    ('general__facility', 523, 'fa4f74e729a9dc7c0581f58c05b4c342bed0ea20446a6f0f6a257810cbf14227', 'facility'),
    ('building__cable_club', 708, 'f6d4fa24a4e611c4b20fd8c95f1def8a8fda35438f61249225c4471bf7e591ba', 'link'),
    ('building__contest', 533, 'd115441d3fd3105a975f7b8f8870f97f4d20d33713ca93cafe00249782eb7905', 'facility'),
]

BACKED_CHAIR_SOURCE_CONTRACTS=[
    ('ruby', 556, '860a596bf7ef1385ec307f61a27aed1fe598005315d85e0ec796e79642fd3f8a', 'west', 'wood'),
    ('ruby', 734, '90a54974c2076c860477933b0b0d741fdac186dabdf609c82ad4a7e5f1ea9a95', 'west', 'stone'),
    ('ruby', 737, 'c52876e92a692f4ba792b00aa06dce4777c22f5dca69882867256ce29c4245c7', 'east', 'house'),
    ('ruby', 738, 'db8383939668476ecf5e8f3294f0edc19850c6973543e895c523eb39617bb909', 'west', 'house'),
    ('ruby', 836, 'e09fa4efa073f1e52d6f05f48413f127d87c9ac50df2bf3a59ec3e44b05d8042', 'east', 'stone'),
    ('ruby', 837, 'df0d86a8277be428ce9e36562d1e2d22bcde0b59753c159f6e520cbc922230d4', 'west', 'stone'),
    ('ruby', 942, '0bb22c5f6061b5035fab16cd35795f3fffff3926f7d5bf08bc541afd8e15d562', 'east', 'house'),
    ('ruby', 943, '771b1128b255a05c4aa23c82dcc419f5d1b2cb0e180f19038f065486cb58b9fc', 'west', 'house'),
    ('sapphire', 556, '860a596bf7ef1385ec307f61a27aed1fe598005315d85e0ec796e79642fd3f8a', 'west', 'wood'),
    ('sapphire', 734, '90a54974c2076c860477933b0b0d741fdac186dabdf609c82ad4a7e5f1ea9a95', 'west', 'stone'),
    ('sapphire', 737, 'c52876e92a692f4ba792b00aa06dce4777c22f5dca69882867256ce29c4245c7', 'east', 'house'),
    ('sapphire', 738, 'db8383939668476ecf5e8f3294f0edc19850c6973543e895c523eb39617bb909', 'west', 'house'),
    ('sapphire', 836, 'e09fa4efa073f1e52d6f05f48413f127d87c9ac50df2bf3a59ec3e44b05d8042', 'east', 'stone'),
    ('sapphire', 837, 'df0d86a8277be428ce9e36562d1e2d22bcde0b59753c159f6e520cbc922230d4', 'west', 'stone'),
    ('sapphire', 942, '0bb22c5f6061b5035fab16cd35795f3fffff3926f7d5bf08bc541afd8e15d562', 'east', 'house'),
    ('sapphire', 943, '771b1128b255a05c4aa23c82dcc419f5d1b2cb0e180f19038f065486cb58b9fc', 'west', 'house'),
    ('emerald', 556, 'ea47e19079f89fcc8feef4d9c9c4080ea81c47a8754abc88e28a4b08a72cbc13', 'west', 'wood'),
    ('emerald', 734, '28e6a22a0cd7ecf9d3459f503fab9412c5c0bf35403ea8ec7dcd44830f6ea6a6', 'west', 'stone'),
    ('emerald', 737, '18fc74c99123a574f31aaee427e206b89f1b64d935ce63f98610cd3eae93448e', 'east', 'house'),
    ('emerald', 738, 'a4c92180f6182d31a8688a9d797b2e114ad44ccb4821079e6bea2a1bc02bebb1', 'west', 'house'),
    ('emerald', 836, '254d1701652940f8e3251651fffe5edd914a584e8cacd2e61669ddb78b876767', 'east', 'stone'),
    ('emerald', 837, '10737b3af059e5d2a8ce08cfed0d641c4caad21ad1e79698662b08373c0d380c', 'west', 'stone'),
    ('emerald', 942, '647913d7dca0b2debd2d6caef5ed562eb81b272589e3c5e735a7303d04b5e3c1', 'east', 'house'),
    ('emerald', 943, '93032e77f0ffd079c267c648e37c687f0d51b53fdfbad9044378a15453859630', 'west', 'house'),
    ('ruby', 555, '4df86d2c7ecf41ff2d41e9b94cb8dcca42f1b5682931610ae0520a6654ee4474', 'east', 'wood'),
    ('sapphire', 555, '4df86d2c7ecf41ff2d41e9b94cb8dcca42f1b5682931610ae0520a6654ee4474', 'east', 'wood'),
    ('emerald', 555, 'cb7fce6f18d5368383d365a299c2152e3669162f3e91994b7d94e52eaa291431', 'east', 'wood'),
]

CLINIC_OBJECT_SOURCE_CONTRACTS=[
    ('ruby', 'bookcase', [[617, 618], [625, 626], [633, 634]], '9ceb5ce6c5dc496e125a9572573d967db586b31836fcfde3a16ce232e65d746d'),
    ('ruby', 'region chart', [[525, 526], [533, 534]], 'f922df644425181c016415abde74c4527d8415d5f375f674a2e8aabbe89acec5'),
    ('ruby', 'display and control', [[586, 587], [594, 595], [519, 603]], 'e82435de3c8710e967a562762b52bd08e049d1a70ec7c534b94b543d061619ec'),
    ('ruby', 'entry rug', [[515, 516]], 'd44ae594f81375af24ea9ccd58d1e73dbffb5795b9db45a6e7b521d9053cdfac'),
    ('ruby', 'floor emblem', [[620, 621, 622, 623], [560, 561, 562, 563], [568, 569, 570, 571], [576, 577, 578, 579]], '26d3493bceeee674fbbf948c5a755462b3f1f98de13a89243805dd628fc7d778'),
    ('sapphire', 'bookcase', [[617, 618], [625, 626], [633, 634]], '9ceb5ce6c5dc496e125a9572573d967db586b31836fcfde3a16ce232e65d746d'),
    ('sapphire', 'region chart', [[525, 526], [533, 534]], 'f922df644425181c016415abde74c4527d8415d5f375f674a2e8aabbe89acec5'),
    ('sapphire', 'display and control', [[586, 587], [594, 595], [519, 603]], 'e82435de3c8710e967a562762b52bd08e049d1a70ec7c534b94b543d061619ec'),
    ('sapphire', 'entry rug', [[515, 516]], 'd44ae594f81375af24ea9ccd58d1e73dbffb5795b9db45a6e7b521d9053cdfac'),
    ('sapphire', 'floor emblem', [[620, 621, 622, 623], [560, 561, 562, 563], [568, 569, 570, 571], [576, 577, 578, 579]], '26d3493bceeee674fbbf948c5a755462b3f1f98de13a89243805dd628fc7d778'),
    ('emerald', 'bookcase', [[617, 618], [625, 626], [633, 634]], '9ceb5ce6c5dc496e125a9572573d967db586b31836fcfde3a16ce232e65d746d'),
    ('emerald', 'region chart', [[525, 526], [533, 534]], 'f922df644425181c016415abde74c4527d8415d5f375f674a2e8aabbe89acec5'),
    ('emerald', 'display and control', [[586, 587], [594, 595], [519, 603]], 'e82435de3c8710e967a562762b52bd08e049d1a70ec7c534b94b543d061619ec'),
    ('emerald', 'entry rug', [[515, 516]], 'd44ae594f81375af24ea9ccd58d1e73dbffb5795b9db45a6e7b521d9053cdfac'),
    ('emerald', 'floor emblem', [[620, 621, 622, 623], [560, 561, 562, 563], [568, 569, 570, 571], [576, 577, 578, 579]], '26d3493bceeee674fbbf948c5a755462b3f1f98de13a89243805dd628fc7d778'),
]

LARGE_DESK_SOURCE_CONTRACTS=[
    ('ruby', 'secret_base__secret_base_tree', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'd8a6dabbfb53528fffb1a9081ffaae9c4a9d525431d445fcf79e430eaa282d50', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_tree', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '4800932819bef2830e0c8525e92d2eee06c4e9923e0b62ceffa54d37874ee907', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_tree', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'dd9fc8139e762463baf57851d53a10df79e4011aac824d6f4ae7900958b785c5', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_tree', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), 'fbe6ee1bfbca751a445f82ed0d9ecc480cb30a15a2b1c775c41d45e689ac66ec', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_tree', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '6d08e348517f5b4db16b49e31c81f54890b8dcdb9e2c378275fe47189bd0be99', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_tree', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), 'dc3e4c4cfd484deccc327c4b01e0c00da8275ae3e0bc5daf7f75c658789900df', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_tree', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), '46a974a88414e95349c6b0d21e7c511b8d25e4572e99247481bf51e9546e024f', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'd05ae4be7bbf403f07a80634e5ba6fca14bf30196f633da464aba90daace9ff4', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '6d6ed372657c2dade1c9e69653554c336be47c4acdc454c2b9a60a0af414d459', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '7d6bb58f7a569a2ba0826a51f06e83a21372b4349e4e16282dad63e57353e8cd', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '3c0ee62cf93bca97c12b06478ea24abc7184b40936f7854e3b7d698cf2bb0cd3', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '0fe9308e1da940370d8b9702b1760f6217ba88cf67bceed2ef56a964dec5b9ad', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '7aeb6c84ce97879cf48e30033428b9afd2b1e10f3993fb0ab338cbd7cac67f72', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_yellow_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'f23c177d56dfdbeaf81e8dfa472ec315016ff8c89c8f43d1e11e77a66c92cc01', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_brown_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '95ef3b843025057acb9c855b74eda886132d37ffb9db5924bad81ed62b9740bb', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_brown_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '8cb6a689034d30cdd6be8eae8c3e3a722effab2d68cb4d067285e547a0602ede', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_brown_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'a3f19842f24cc219f5d87a949ad9b3c62a09d599f9e5c18e733e09d032d8051e', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_brown_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2fdf0310aea317e5f07060614a3148d5af0f01f312da61fa08d5a4fd46c674b7', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_brown_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '9bd998b64f0f26e0cb55e535d0b15a6b4f55c6f985ba33a12c19ac68b99cb339', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_brown_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '0ccefd0797e3c3a8bf833419666209e980825ae55df7cb77a459bb40e674e4a3', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_brown_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'fd33311ac16dde03f084b98c58a9c095f6398c61e70c5e0605c4cab098477e79', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_red_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '957ef5e3ab820cf22fed4292664f9199821e514b4c61a95206c0e2743159a4ee', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_red_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '800e7a28f79c24f391be711a9475a69145bac6bfccd9acc10ecaa5cbd9977fb1', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_red_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'ec1ed96c9da1478d261650de08b1c588066b1af2098283c50e1d5483f4e54c84', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_red_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2e1dcc0921b04a6ef7f75913ff3e9961aeaac09da103bf4a553f07128f34c92f', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_red_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '98aa982ba4990473f6ee3b7de9dec099ba5bcb6030871e47a3153b37390ef8f1', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_red_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '9679f09dffde45f51b16a1adc41fe23c1c0e233bc268d9799a3eafad6ede9bdd', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_red_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'd053370b022b6075cdf27bf61c7e9d2722614723ffc8e760d3aba6d5b660c69c', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_shrub', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'a29f041151a412b0da7b3aa0868dc8f530c96dc2063463d887173aac3c71a0f3', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_shrub', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '3b4bed74dc03f29f1b90ae3842b7bcba763887138e0819bd929b8b7298bc5fd1', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_shrub', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '0f88b2fd79e38c263b39d4a01ebad8a6f7ae206e916e4213391a6f5463caab08', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_shrub', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '04c4b4da584908d15935fbdbf3df1b0514a3641b37719cd81f763b3b01f32c82', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_shrub', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '5251283e192a3d8cfa0aa94b4d776bbcbb334701823492c9b91f7f71e8036f08', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_shrub', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '22877af6f9c26a20bfd689b4e54f98d72e1766030a817eef67d4f95f96762b28', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_shrub', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'a6f66b3436898e63be1e9d40fda96642cff24a3c90786ae75fe2a21a437aa4ed', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_blue_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '9f09e46092a26e6d02590da3eb98d79c3d4e3459f30249175eb7301d7655b372', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_blue_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '9668bbdeaeb1ede3b9f3328d00bc2de6be805dcfb7b16a59b9f7ad43526f95d9', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_blue_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '507d9d365a986982efcaf9077dff62a38ef7344a8db00f3e6bac8cf2ec8f14ef', (437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_blue_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2a823da9ac17ce6fb7f668af2d828790402d1d8904bae142e707ac43563f4bf2', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_blue_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '9304e2cb300e20bf99c7fe29ea33fb509115a0bc0baead1f80cd79cba5901649', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_blue_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '9d048b3ed1c3572c33355299a099c461a29d1d106ceecfda3bbc3345b726e433', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('ruby', 'secret_base__secret_base_blue_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), '922ca195d1049b29743491eb8640df29d12f65ffe9a10202768d9b741cd3e2e0', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_tree', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'd8a6dabbfb53528fffb1a9081ffaae9c4a9d525431d445fcf79e430eaa282d50', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_tree', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '4800932819bef2830e0c8525e92d2eee06c4e9923e0b62ceffa54d37874ee907', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_tree', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'dd9fc8139e762463baf57851d53a10df79e4011aac824d6f4ae7900958b785c5', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_tree', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), 'fbe6ee1bfbca751a445f82ed0d9ecc480cb30a15a2b1c775c41d45e689ac66ec', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_tree', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '6d08e348517f5b4db16b49e31c81f54890b8dcdb9e2c378275fe47189bd0be99', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_tree', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), 'dc3e4c4cfd484deccc327c4b01e0c00da8275ae3e0bc5daf7f75c658789900df', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_tree', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), '46a974a88414e95349c6b0d21e7c511b8d25e4572e99247481bf51e9546e024f', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'd05ae4be7bbf403f07a80634e5ba6fca14bf30196f633da464aba90daace9ff4', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '6d6ed372657c2dade1c9e69653554c336be47c4acdc454c2b9a60a0af414d459', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '7d6bb58f7a569a2ba0826a51f06e83a21372b4349e4e16282dad63e57353e8cd', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '3c0ee62cf93bca97c12b06478ea24abc7184b40936f7854e3b7d698cf2bb0cd3', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '0fe9308e1da940370d8b9702b1760f6217ba88cf67bceed2ef56a964dec5b9ad', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '7aeb6c84ce97879cf48e30033428b9afd2b1e10f3993fb0ab338cbd7cac67f72', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_yellow_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'f23c177d56dfdbeaf81e8dfa472ec315016ff8c89c8f43d1e11e77a66c92cc01', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '95ef3b843025057acb9c855b74eda886132d37ffb9db5924bad81ed62b9740bb', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '8cb6a689034d30cdd6be8eae8c3e3a722effab2d68cb4d067285e547a0602ede', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'a3f19842f24cc219f5d87a949ad9b3c62a09d599f9e5c18e733e09d032d8051e', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2fdf0310aea317e5f07060614a3148d5af0f01f312da61fa08d5a4fd46c674b7', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '9bd998b64f0f26e0cb55e535d0b15a6b4f55c6f985ba33a12c19ac68b99cb339', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '0ccefd0797e3c3a8bf833419666209e980825ae55df7cb77a459bb40e674e4a3', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_brown_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'fd33311ac16dde03f084b98c58a9c095f6398c61e70c5e0605c4cab098477e79', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_red_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '957ef5e3ab820cf22fed4292664f9199821e514b4c61a95206c0e2743159a4ee', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_red_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '800e7a28f79c24f391be711a9475a69145bac6bfccd9acc10ecaa5cbd9977fb1', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_red_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'ec1ed96c9da1478d261650de08b1c588066b1af2098283c50e1d5483f4e54c84', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_red_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2e1dcc0921b04a6ef7f75913ff3e9961aeaac09da103bf4a553f07128f34c92f', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_red_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '98aa982ba4990473f6ee3b7de9dec099ba5bcb6030871e47a3153b37390ef8f1', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_red_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '9679f09dffde45f51b16a1adc41fe23c1c0e233bc268d9799a3eafad6ede9bdd', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_red_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'd053370b022b6075cdf27bf61c7e9d2722614723ffc8e760d3aba6d5b660c69c', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_shrub', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'a29f041151a412b0da7b3aa0868dc8f530c96dc2063463d887173aac3c71a0f3', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_shrub', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '3b4bed74dc03f29f1b90ae3842b7bcba763887138e0819bd929b8b7298bc5fd1', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_shrub', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '0f88b2fd79e38c263b39d4a01ebad8a6f7ae206e916e4213391a6f5463caab08', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_shrub', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '04c4b4da584908d15935fbdbf3df1b0514a3641b37719cd81f763b3b01f32c82', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_shrub', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '5251283e192a3d8cfa0aa94b4d776bbcbb334701823492c9b91f7f71e8036f08', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_shrub', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '22877af6f9c26a20bfd689b4e54f98d72e1766030a817eef67d4f95f96762b28', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_shrub', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'a6f66b3436898e63be1e9d40fda96642cff24a3c90786ae75fe2a21a437aa4ed', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '9f09e46092a26e6d02590da3eb98d79c3d4e3459f30249175eb7301d7655b372', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '9668bbdeaeb1ede3b9f3328d00bc2de6be805dcfb7b16a59b9f7ad43526f95d9', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '507d9d365a986982efcaf9077dff62a38ef7344a8db00f3e6bac8cf2ec8f14ef', (437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2a823da9ac17ce6fb7f668af2d828790402d1d8904bae142e707ac43563f4bf2', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '9304e2cb300e20bf99c7fe29ea33fb509115a0bc0baead1f80cd79cba5901649', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '9d048b3ed1c3572c33355299a099c461a29d1d106ceecfda3bbc3345b726e433', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('sapphire', 'secret_base__secret_base_blue_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), '922ca195d1049b29743491eb8640df29d12f65ffe9a10202768d9b741cd3e2e0', (437, 451, 437, 437, 451, 437, 441, 441, 441)),
    ('emerald', 'secret_base__secret_base_tree', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'd8a6dabbfb53528fffb1a9081ffaae9c4a9d525431d445fcf79e430eaa282d50', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_tree', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '4800932819bef2830e0c8525e92d2eee06c4e9923e0b62ceffa54d37874ee907', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_tree', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'dd9fc8139e762463baf57851d53a10df79e4011aac824d6f4ae7900958b785c5', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_tree', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), 'fbe6ee1bfbca751a445f82ed0d9ecc480cb30a15a2b1c775c41d45e689ac66ec', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_tree', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '6d08e348517f5b4db16b49e31c81f54890b8dcdb9e2c378275fe47189bd0be99', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_tree', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), 'dc3e4c4cfd484deccc327c4b01e0c00da8275ae3e0bc5daf7f75c658789900df', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_tree', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), '46a974a88414e95349c6b0d21e7c511b8d25e4572e99247481bf51e9546e024f', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'd05ae4be7bbf403f07a80634e5ba6fca14bf30196f633da464aba90daace9ff4', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '6d6ed372657c2dade1c9e69653554c336be47c4acdc454c2b9a60a0af414d459', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '7d6bb58f7a569a2ba0826a51f06e83a21372b4349e4e16282dad63e57353e8cd', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '3c0ee62cf93bca97c12b06478ea24abc7184b40936f7854e3b7d698cf2bb0cd3', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '0fe9308e1da940370d8b9702b1760f6217ba88cf67bceed2ef56a964dec5b9ad', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '7aeb6c84ce97879cf48e30033428b9afd2b1e10f3993fb0ab338cbd7cac67f72', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_yellow_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'f23c177d56dfdbeaf81e8dfa472ec315016ff8c89c8f43d1e11e77a66c92cc01', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_red_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '957ef5e3ab820cf22fed4292664f9199821e514b4c61a95206c0e2743159a4ee', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_red_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '800e7a28f79c24f391be711a9475a69145bac6bfccd9acc10ecaa5cbd9977fb1', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_red_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'ec1ed96c9da1478d261650de08b1c588066b1af2098283c50e1d5483f4e54c84', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_red_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2e1dcc0921b04a6ef7f75913ff3e9961aeaac09da103bf4a553f07128f34c92f', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_red_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '98aa982ba4990473f6ee3b7de9dec099ba5bcb6030871e47a3153b37390ef8f1', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_red_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '9679f09dffde45f51b16a1adc41fe23c1c0e233bc268d9799a3eafad6ede9bdd', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_red_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'd053370b022b6075cdf27bf61c7e9d2722614723ffc8e760d3aba6d5b660c69c', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_blue_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '9f09e46092a26e6d02590da3eb98d79c3d4e3459f30249175eb7301d7655b372', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_blue_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '9668bbdeaeb1ede3b9f3328d00bc2de6be805dcfb7b16a59b9f7ad43526f95d9', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_blue_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '507d9d365a986982efcaf9077dff62a38ef7344a8db00f3e6bac8cf2ec8f14ef', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_blue_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2a823da9ac17ce6fb7f668af2d828790402d1d8904bae142e707ac43563f4bf2', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_blue_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '9304e2cb300e20bf99c7fe29ea33fb509115a0bc0baead1f80cd79cba5901649', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_blue_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '9d048b3ed1c3572c33355299a099c461a29d1d106ceecfda3bbc3345b726e433', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_blue_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), '922ca195d1049b29743491eb8640df29d12f65ffe9a10202768d9b741cd3e2e0', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_brown_cave', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), '95ef3b843025057acb9c855b74eda886132d37ffb9db5924bad81ed62b9740bb', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_brown_cave', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '8cb6a689034d30cdd6be8eae8c3e3a722effab2d68cb4d067285e547a0602ede', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_brown_cave', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), 'a3f19842f24cc219f5d87a949ad9b3c62a09d599f9e5c18e733e09d032d8051e', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_brown_cave', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '2fdf0310aea317e5f07060614a3148d5af0f01f312da61fa08d5a4fd46c674b7', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_brown_cave', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '9bd998b64f0f26e0cb55e535d0b15a6b4f55c6f985ba33a12c19ac68b99cb339', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_brown_cave', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '0ccefd0797e3c3a8bf833419666209e980825ae55df7cb77a459bb40e674e4a3', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_brown_cave', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'fd33311ac16dde03f084b98c58a9c095f6398c61e70c5e0605c4cab098477e79', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_shrub', 'HEAVY DESK', 3, (3, 2), (656, 657, 658, 664, 665, 666), 'a29f041151a412b0da7b3aa0868dc8f530c96dc2063463d887173aac3c71a0f3', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_shrub', 'RAGGED DESK', 4, (3, 2), (659, 660, 661, 667, 668, 669), '3b4bed74dc03f29f1b90ae3842b7bcba763887138e0819bd929b8b7298bc5fd1', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_shrub', 'COMFORT DESK', 5, (3, 2), (662, 663, 675, 670, 671, 683), '0f88b2fd79e38c263b39d4a01ebad8a6f7ae206e916e4213391a6f5463caab08', (437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_shrub', 'PRETTY DESK', 6, (3, 3), (701, 702, 703, 709, 710, 711, 717, 718, 719), '04c4b4da584908d15935fbdbf3df1b0514a3641b37719cd81f763b3b01f32c82', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_shrub', 'BRICK DESK', 7, (3, 3), (672, 673, 674, 680, 681, 682, 688, 689, 690), '5251283e192a3d8cfa0aa94b4d776bbcbb334701823492c9b91f7f71e8036f08', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_shrub', 'CAMP DESK', 8, (3, 3), (676, 677, 678, 684, 685, 686, 692, 693, 694), '22877af6f9c26a20bfd689b4e54f98d72e1766030a817eef67d4f95f96762b28', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
    ('emerald', 'secret_base__secret_base_shrub', 'HARD DESK', 9, (3, 3), (679, 699, 700, 687, 707, 708, 695, 715, 716), 'a6f66b3436898e63be1e9d40fda96642cff24a3c90786ae75fe2a21a437aa4ed', (437, 451, 437, 437, 451, 437, 454, 454, 454)),
]

CLINIC_STRUCTURE_SOURCE_CONTRACTS=[
    ('ruby', 517, '5b08c9dd52608fee00fd37c5f6c014c2b7c58f3a63c03ea8a084388de86a8dff', 128),
    ('ruby', 520, '0de43789432a076dd56a01adcb631822811213d104c6ce5851650741faa152fc', 0),
    ('ruby', 527, '42bfe17d5ee627faac69e90838c5eb3b1fa3fb9552ac98d4007a6e8f0c06b979', 0),
    ('ruby', 528, 'c01a21d03539988514d98d1225715070102c7d4dbd522771c899b016c0552c80', 0),
    ('ruby', 535, 'd553163a9344a31bd0cdc82e920ea407f9751cf15e017b77312838a26cf2675d', 0),
    ('ruby', 536, '8b9c789ed64dd5f9a87e44a0c8035ac481ed6e202f920e080771a33479c4d404', 0),
    ('ruby', 543, '03fb1b84d0ee794bddfe80bc35fd26c04df461c26a40d565ff1be7789a654d6c', 0),
    ('ruby', 552, '89f846b554f892d2d735a516cd1a698e91e04ea994e8978f443d2dbed240bc7d', 0),
    ('ruby', 567, 'c5bd841ce80953853013133c395a351aeb2f0f8d7e2c5c5b3a5c0f113c3848cf', 0),
    ('ruby', 640, '810dadcf0fc58f8a100cabc19645a2d0423a1d293574efb62b1e0b7f0f1abf96', 0),
    ('ruby', 641, '8ab6805a12acfcf91637a0d4924636a42fe6b5ba1c48931c1dd91253191f6a56', 0),
    ('ruby', 648, 'b6f14e172ab0294cdd065cb44de61bf3b762e442f9b0dcf98e06805253528a29', 0),
    ('ruby', 649, '1e042049c6f8835857f04e8abec2b053db93dd693acf91b266b5e8fbd2fcc231', 106),
    ('ruby', 656, '7c97d89c3e20e3d54f5dde5f7d67ab4784f8fbf0dbd36fa06819b8e18ad3febc', 0),
    ('ruby', 657, '43cd6e4efe1e85fba4fe044d3ef9295faaaee2586eed38b5a4bd0cfbaa66dc6e', 0),
    ('sapphire', 517, '5b08c9dd52608fee00fd37c5f6c014c2b7c58f3a63c03ea8a084388de86a8dff', 128),
    ('sapphire', 520, '0de43789432a076dd56a01adcb631822811213d104c6ce5851650741faa152fc', 0),
    ('sapphire', 527, '42bfe17d5ee627faac69e90838c5eb3b1fa3fb9552ac98d4007a6e8f0c06b979', 0),
    ('sapphire', 528, 'c01a21d03539988514d98d1225715070102c7d4dbd522771c899b016c0552c80', 0),
    ('sapphire', 535, 'd553163a9344a31bd0cdc82e920ea407f9751cf15e017b77312838a26cf2675d', 0),
    ('sapphire', 536, '8b9c789ed64dd5f9a87e44a0c8035ac481ed6e202f920e080771a33479c4d404', 0),
    ('sapphire', 543, '03fb1b84d0ee794bddfe80bc35fd26c04df461c26a40d565ff1be7789a654d6c', 0),
    ('sapphire', 552, '89f846b554f892d2d735a516cd1a698e91e04ea994e8978f443d2dbed240bc7d', 0),
    ('sapphire', 567, 'c5bd841ce80953853013133c395a351aeb2f0f8d7e2c5c5b3a5c0f113c3848cf', 0),
    ('sapphire', 640, '810dadcf0fc58f8a100cabc19645a2d0423a1d293574efb62b1e0b7f0f1abf96', 0),
    ('sapphire', 641, '8ab6805a12acfcf91637a0d4924636a42fe6b5ba1c48931c1dd91253191f6a56', 0),
    ('sapphire', 648, 'b6f14e172ab0294cdd065cb44de61bf3b762e442f9b0dcf98e06805253528a29', 0),
    ('sapphire', 649, '1e042049c6f8835857f04e8abec2b053db93dd693acf91b266b5e8fbd2fcc231', 106),
    ('sapphire', 656, '7c97d89c3e20e3d54f5dde5f7d67ab4784f8fbf0dbd36fa06819b8e18ad3febc', 0),
    ('sapphire', 657, '43cd6e4efe1e85fba4fe044d3ef9295faaaee2586eed38b5a4bd0cfbaa66dc6e', 0),
    ('emerald', 517, '5b08c9dd52608fee00fd37c5f6c014c2b7c58f3a63c03ea8a084388de86a8dff', 128),
    ('emerald', 520, '0de43789432a076dd56a01adcb631822811213d104c6ce5851650741faa152fc', 0),
    ('emerald', 527, '42bfe17d5ee627faac69e90838c5eb3b1fa3fb9552ac98d4007a6e8f0c06b979', 0),
    ('emerald', 528, 'c01a21d03539988514d98d1225715070102c7d4dbd522771c899b016c0552c80', 0),
    ('emerald', 535, 'd553163a9344a31bd0cdc82e920ea407f9751cf15e017b77312838a26cf2675d', 0),
    ('emerald', 536, '8b9c789ed64dd5f9a87e44a0c8035ac481ed6e202f920e080771a33479c4d404', 0),
    ('emerald', 543, '03fb1b84d0ee794bddfe80bc35fd26c04df461c26a40d565ff1be7789a654d6c', 0),
    ('emerald', 552, '89f846b554f892d2d735a516cd1a698e91e04ea994e8978f443d2dbed240bc7d', 0),
    ('emerald', 567, 'c5bd841ce80953853013133c395a351aeb2f0f8d7e2c5c5b3a5c0f113c3848cf', 0),
    ('emerald', 640, '810dadcf0fc58f8a100cabc19645a2d0423a1d293574efb62b1e0b7f0f1abf96', 0),
    ('emerald', 641, '8ab6805a12acfcf91637a0d4924636a42fe6b5ba1c48931c1dd91253191f6a56', 0),
    ('emerald', 648, 'b6f14e172ab0294cdd065cb44de61bf3b762e442f9b0dcf98e06805253528a29', 0),
    ('emerald', 649, '1e042049c6f8835857f04e8abec2b053db93dd693acf91b266b5e8fbd2fcc231', 106),
    ('emerald', 656, '7c97d89c3e20e3d54f5dde5f7d67ab4784f8fbf0dbd36fa06819b8e18ad3febc', 0),
    ('emerald', 657, '43cd6e4efe1e85fba4fe044d3ef9295faaaee2586eed38b5a4bd0cfbaa66dc6e', 0),
]

MOSSDEEP_SYMBOL_SOURCE_CONTRACTS=[
    ('ruby', 513, '2700852141cc44a5d10f6da38949041eb66d806062b887f5912a7abb3d8441a4', 68, 'east'),
    ('ruby', 514, '4a78ab06816a79fb550ca0f1b7c6031465fd65bcc6064c608491cd6797056f53', 71, 'south'),
    ('ruby', 515, '1eaba94ff051e0de5f323a64da6b70117aa6eb33485315177541e17352660b53', 71, 'south'),
    ('ruby', 522, '4d075c743d9079df047cea07caa0914604893cf2b27ba097b549ead8e4aea1d6', 70, 'north'),
    ('ruby', 524, '24f427c48266598afce1f9ea48281b6d90974d383eb4b7a8c24f0ca89deee035', 65, 'west'),
    ('sapphire', 513, '2700852141cc44a5d10f6da38949041eb66d806062b887f5912a7abb3d8441a4', 68, 'east'),
    ('sapphire', 514, '4a78ab06816a79fb550ca0f1b7c6031465fd65bcc6064c608491cd6797056f53', 71, 'south'),
    ('sapphire', 515, '1eaba94ff051e0de5f323a64da6b70117aa6eb33485315177541e17352660b53', 71, 'south'),
    ('sapphire', 522, '4d075c743d9079df047cea07caa0914604893cf2b27ba097b549ead8e4aea1d6', 70, 'north'),
    ('sapphire', 524, '24f427c48266598afce1f9ea48281b6d90974d383eb4b7a8c24f0ca89deee035', 65, 'west'),
]

def scoped(pair,mid):return(pair.startswith(('building__','secret_base__'))or(pair in GENERAL_INTERIORS and mid>=512))and not(pair=='general__facility'and mid in FACILITY_OUTDOORS)
def identity(row):return row['game'],row['style'],row['tileset'],row['id'],row.get('map')

class Review(ReverseReview):
    def __init__(self):
        super().__init__('gen2-hoenn-interior-finish',GAMES);self.prior=[];self.origins={};self.held=[];self.contracts=[];self.independent_sources=set()
        for name in dict.fromkeys(re.findall(r'''['\"](mappings/[^'\"]+\.lua)['\"]''',(ROOT/'main.lua').read_text())):
            if name==TARGET.relative_to(ROOT).as_posix():continue
            for i,row in enumerate(preview.read_reviewed(ROOT/name),1):
                self.prior.append(row);self.origins[id(row)]=(name,i)
        self.occupied={identity(r)for r in self.prior if r['game']in GAMES and r['style']=='gen2'}
        self.scope={g:{key:c for key,c in self.imp.cell_index(g).items()if scoped(*key)and c.get('used_by_map_count')}for g in GAMES}
        borders=ROOT.parent/'.work/tileshift-v0320-native-border-inventory.json'
        self.border_keys=[];self.intentional_exclusions=[];self.dynamic_sources=[]
        if borders.exists():
            for item in json.loads(borders.read_text())['all_border']:
                if item['game']not in GAMES or not scoped(item['pair'],item['id']):continue
                cell=self.imp.cell_index(item['game']).get((item['pair'],item['id']))
                if cell:self.scope[item['game']][item['pair'],item['id']]=cell;self.border_keys.append(item)
                else:self.intentional_exclusions.append(dict(**item,reason='Unavailable empty native atlas slot. The actual source renderer leaves this camera border black, already identical to classic black; keep native black without inventing a fingerprint.'))
        # Actual procedural map inputs, not every unused metatile in a bank.
        hill=self.imp.table('emerald','gba/rse/trainer_hill/manifest')
        hill_mids=set()
        for challenge in hill['challenges']:
            for floor in challenge['floors']:hill_mids.update(int(n)+512 for n in floor['map']['metatiles'])
        self.runtime_scope('building__trainer_hill',hill_mids,'Trainer Hill actual challenges[].floors[].map.metatiles + runtime NUM_METATILES_IN_PRIMARY512')
        pyramid=self.imp.table('emerald','gba/rse/pyramid/manifest');manifest=self.imp.table('emerald','gba/native/manifest')
        template_ids={0}|{int(option[1])for option in pyramid['floorTemplateOptions']};offsets=set()
        for i in template_ids:offsets.update(int(n)for n in pyramid['floorTemplates'][i]['layoutOffsets'])
        pyramid_mids=set();squares=[]
        for offset in sorted(offsets):
            name='EM_BATTLE_PYRAMID_SQUARE'+f'{offset+1:02d}';spec=manifest['layouts'].get(name)
            if not spec:self.held.append(dict(game='emerald',map=name,reason='Actual Pyramid template square has no imported native layout.'));continue
            layout=decode_layout(self.cache/'emerald/data/generated/gba/native'/spec['file']);pyramid_mids.update(layout['mids']);squares.append(name)
        constants=catalog.read_lua(ROOT.parent/'.tools/engine-0395/src/core/game3/constants/emerald/metatile_labels.lua')['byName']
        pyramid_mids.update(constants[name]for name in('METATILE_BattlePyramid_Floor','METATILE_BattlePyramid_Exit'))
        self.runtime_scope('building__battle_pyramid',pyramid_mids,'Pyramid reachable floorTemplateOptions/layoutOffsets square layouts plus actual Floor/Exit runtime rewrite labels',squares)
        self.secret_base_scope()

    def runtime_scope(self,pair,mids,reason,maps=(),game='emerald'):
        added=[];missing=[]
        for mid in sorted(mids):
            cell=self.imp.cell_index(game).get((pair,mid))
            if cell:
                if(pair,mid)not in self.scope[game]:added.append(mid)
                self.scope[game][pair,mid]=cell
            else:missing.append(mid);self.held.append(dict(game=game,pair=pair,id=mid,reason='Actual procedural source MID is absent from the imported native bank; no invented source image/hash.',possible_equivalent='Review complete native floor/wall counterpart after source pixels are available.'))
        self.dynamic_sources.append(dict(game=game,pair=pair,source=reason,maps=list(maps),actual_ids=sorted(mids),new_ids=added,missing_ids=missing))

    def secret_base_scope(self):
        shapes={0:(1,1),1:(2,1),2:(3,1),3:(4,2),4:(2,2),5:(1,2),6:(1,3),7:(2,4),8:(3,3),9:(3,2)}
        labels=['BlueBalloon','CuteTV','GoldShield_Base1','Ground','MudBall','PC','RedBalloon','RegisterPC','RoundTV',
            'SandOrnament_BrokenBase','SilverShield_Base1','Slide_SlideTop','Slide_StairLanding','SolidBoard_Bottom','SolidBoard_Top',
            'Stand_CornerLeft','Stand_CornerRight','TV','YellowBalloon']
        self.decorations=[]
        for game in GAMES:
            pack=self.imp.table(game,'gba/secret_base/manifest');definitions=self.imp.table(game,'gba/decorations/decorations')['decorations'];mids=set();records=[]
            for did,d in definitions.items():
                if int(did)==0 or d['permission']==4:continue
                width,height=shapes[d['shape']];tiles=catalog.lua_array(pack['decorTiles'][str(did)]);assert len(tiles)==width*height
                base=[int(t)+512 for t in tiles];mids.update(base)
                walls=[int(t)+513 for t in tiles[:width]]if d['permission']==2 else[];mids.update(walls)
                records.append(dict(id=int(did),name=d['name'],permission=d['permission'],shape=[width,height],metatiles=base,top_row_wall_variants=walls))
            version='emerald'if game=='emerald'else'ruby'
            constants=catalog.read_lua(ROOT.parent/'.tools/engine-0395/src/core/game3/constants'/version/'metatile_labels.lua')['byName']
            runtime={name:int(constants['METATILE_SecretBase_'+name])for name in labels if'METATILE_SecretBase_'+name in constants};mids.update(runtime.values())
            assert len(records)==75 and len(mids)==(254 if game=='emerald' else 250),('Actual Secret Base reachable inventory changed',game,len(records),len(mids))
            pairs=[p for p in self.imp.table(game,'gba/native/manifest')['pairs']if p.startswith('secret_base__secret_base_')];assert len(pairs)==6
            for pair in pairs:self.runtime_scope(pair,mids,'Actual non-sprite decorations +512; BEHIND_FLOOR top-row north-wall +1 only, and literal Secret Base runtime state labels',game=game)
            self.decorations.append(dict(game=game,definitions=records,runtime_labels=runtime,actual_ids=sorted(mids),source_manifest='gba/secret_base/manifest',source_definitions='gba/decorations/decorations',sprite_decorations_excluded=True))

    def gb_image(self,ref):
        if ref.get('game')=='crystal'and ref.get('monochrome'):
            ts=self.imp.table('crystal','tilesets')[ref['tileset']];sheet=Image.open(self.cache/'crystal'/ts['image']).convert('RGBA');block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));image=preview.native_cell(sheet,ts,block,ref['quadrant'])
            assert catalog.sha(image.tobytes())==ref['hash']and set(image.get_flattened_data())=={(0,0,0,255)},'Only an exact native black glyph may bypass the Crystal DAY palette for black canvas preservation'
            return image
        return super().gb_image(ref)

    def inventory(self):
        records=[];pairs=[]
        for game in GAMES:
            groups=defaultdict(list)
            manifest=self.imp.table(game,'gba/native/manifest')
            maps=defaultdict(list)
            for name,spec in manifest['layouts'].items():maps[spec['pair']].append(name)
            for(pair,mid),c in self.scope[game].items():groups[pair].append((mid,c))
            for pair,items in sorted(groups.items()):
                existing=sum((game,'gen2',pair,mid,None)in self.occupied for mid,c in items)
                pairs.append(dict(game=game,pair=pair,used_cells=len(items),existing=existing,remaining=len(items)-existing,maps=sorted(maps[pair])))
                for mid,c in sorted(items):records.append(dict(game=game,pair=pair,id=mid,sourceHash=c['pixel_sha256'],behavior=c.get('behavior'),used_by_maps=c.get('used_by_map_count'),existing=(game,'gen2',pair,mid,None)in self.occupied))
        (self.out/'inventory.json').write_bytes((json.dumps(dict(pairs=pairs,cells=records),indent=2)+'\n').encode())
        print(json.dumps(dict(source_cells=len(records),already_mapped=sum(r['existing']for r in records),pairs=len(pairs),by_game=dict(Counter(r['game']for r in records))),indent=2))
        return records

    def contacts(self,pair='building__generic_building',game='emerald'):
        items=sorted((mid,c)for(p,mid),c in self.scope[game].items()if p==pair);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12);cw,ch=52,66
        for start in range(0,len(items),128):
            im=Image.new('RGB',(cw*16,ch*8),'#18202c');d=ImageDraw.Draw(im)
            for i,(mid,c)in enumerate(items[start:start+128]):
                ref=dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']);cell=preview.native_donor(self.cache,ref,self.packed);x,y=i%16*cw,i//16*ch
                im.paste(cell.resize((48,48),Image.Resampling.NEAREST),(x+2,y+17));d.text((x+2,y+1),str(mid)+('*'if(game,'gen2',pair,mid,None)in self.occupied else''),fill='white',font=font)
            im.save(self.out/(game+'-'+pair+f'-contact-{start//128+1:02}.png'))

    def previews(self):
        authored=self.rows;self.rows={identity(r):r for r in self.prior if r['game']in GAMES and r['style']=='gen2'};self.rows.update(authored)
        scenes=[]
        for game,prefix in [('ruby','RU'),('sapphire','SA'),('emerald','EM')]:
            manifest=self.imp.table(game,'gba/native/manifest')['layouts']
            for suffix in ['DEWFORD_TOWN_HOUSE1','DEWFORD_TOWN_HALL','OLDALE_TOWN_POKEMON_CENTER_1F','OLDALE_TOWN_MART',
                           'VERDANTURF_TOWN_WANDAS_HOUSE','MOSSDEEP_CITY_STEVENS_HOUSE','ROUTE119_HOUSE','RUSTBORO_CITY_CUTTERS_HOUSE',
                           'SOOTOPOLIS_CITY_HOUSE2','RUSTBORO_CITY_GYM','MAUVILLE_CITY_GYM','ROUTE110_TRICK_HOUSE_PUZZLE1']:
                name=prefix+'_'+suffix
                if name in manifest:scenes.append(self.map_preview(game,name,'gen2'))
        records=[];objects=[('clinic-storage','building__pokemon_center',[[584,585],[592,593],[600,601]]),
            ('clinic-healer','building__pokemon_center',[[546,547],[554,555]]),('clinic-computer','building__pokemon_center',[[524],[4],[548]]),
            ('clinic-plant','building__pokemon_center',[[521],[529],[537]]),
            ('house-window','building__generic_building',[[702,703],[710,711],[718,719]]),
            ('house-cabinet','building__generic_building',[[678,679],[686,687],[694,695]]),
            ('bed','building__generic_building',[[723,724],[731,732]]),('dining-mug','building__generic_building',[[584,585],[592,593]]),
            ('large-table','building__generic_building',[[744,745,745,746],[752,753,753,754]]),
            ('potted-tree','building__generic_building',[[656],[664]]),('television','building__generic_building',[[2]]),
            ('clinic-stock-bookcase','building__pokemon_center',[[617,618],[625,626],[633,634]]),
            ('clinic-region-chart','building__pokemon_center',[[525,526],[533,534]]),
            ('clinic-display-control','building__pokemon_center',[[586,587],[594,595],[519,603]]),
            ('clinic-floor-emblem','building__pokemon_center',[[620,621,622,623],[560,561,562,563],[568,569,570,571],[576,577,578,579]]),
            ('clinic-whole-stairs','building__pokemon_center',[[640,641],[648,649],[656,657]])]
        for design in self.decorations[-1]['definitions']:
            if design['name'].endswith(('DESK','CHAIR')):
                w,h=design['shape'];ids=design['metatiles'];objects.append(('secret-base-'+design['name'].lower().replace('é','e').replace(' ','-'),
                    'secret_base__secret_base_red_cave',[ids[y*w:(y+1)*w]for y in range(h)]))
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
        for label,pair,layout in objects:
            w,h=len(layout[0])*16,len(layout)*16;before=Image.new('RGBA',(w,h));after=Image.new('RGBA',(w,h));complete=True
            for y,row in enumerate(layout):
                for x,mid in enumerate(row):
                    source=self.imp.cell_index('emerald')[pair,mid];ref=dict(game='emerald',tileset=pair,id=mid,hash=source['pixel_sha256'])
                    before.paste(preview.native_donor(self.cache,ref,self.packed),(x*16,y*16));chosen=self.rows.get(('emerald','gen2',pair,mid,None))
                    if not chosen:complete=False;break
                    after.paste(self.render(chosen),(x*16,y*16))
            if not complete:continue
            scale=5;panel=Image.new('RGB',(w*scale*2+54,h*scale+70),'#18202c');d=ImageDraw.Draw(panel)
            d.text((12,8),label+' — complete native pixels, development artwork',font=font,fill='white')
            first=before.convert('RGB').resize((w*scale,h*scale),Image.Resampling.NEAREST);second=after.convert('RGB').resize((w*scale,h*scale),Image.Resampling.NEAREST)
            panel.paste(first,(12,35));panel.paste(second,(36+w*scale,35));path=self.out/(label+'-whole-comparison.png');panel.save(path)
            saved=Image.open(path).convert('RGB');assert saved.crop((12,35,12+w*scale,35+h*scale)).tobytes()==first.tobytes();assert saved.crop((36+w*scale,35,36+w*scale+w*scale,35+h*scale)).tobytes()==second.tobytes()
            records.append(dict(label=label,path=str(path),sha256=catalog.sha(path.read_bytes()),pair=pair,source_ids=layout,pixel_scale=scale,panels_exact_after_save=True,actors_rendered=False))
        self.rows=authored
        (self.out/'scene-coverage.json').write_text(json.dumps(scenes,indent=2));(self.out/'whole-object-preview-proof.json').write_text(json.dumps(records,indent=2))

    def add(self,game,pair,mid,art,evidence):
        if(game,'gen2',pair,mid,None)in self.occupied:return
        previous=self.rows.get((game,'gen2',pair,mid,None))
        if previous:
            assert previous['compositionPixelHash']==catalog.sha(self.render(art).tobytes())and previous.get('overMask')==art.get('overMask'),('Different shared complete-object output',game,pair,mid)
            return
        self.row(game,pair,mid,'gen2',art,evidence)

    def primitive(self,role):
        witness=next(r for r in self.prior if r['game']=='crystal'and r['style']=='gen3'and r['role']==role)
        return donor_ref(self,witness)

    def neutral(self,ref):
        if not hasattr(self,'_neutral_cells'):self._neutral_cells={};self._neutral_sheets={}
        if ref['hash']not in self._neutral_cells:
            ts=self.imp.table('crystal','tilesets')[ref['tileset']]
            if ref['tileset']not in self._neutral_sheets:self._neutral_sheets[ref['tileset']]=Image.open(self.cache/'crystal'/ts['image']).convert('RGBA')
            block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));im=preview.native_cell(self._neutral_sheets[ref['tileset']],ts,block,ref['quadrant'])
            assert catalog.sha(im.tobytes())==ref['hash'];self._neutral_cells[ref['hash']]=im
        return self._neutral_cells[ref['hash']]

    def validate(self):
        sources=[]
        for row in self.rows.values():
            ref=dict(game=row['game'],tileset=row['tileset'],id=row['id'],hash=row['sourceHash'])
            image=preview.native_donor(self.cache,ref,self.packed)
            assert catalog.sha(image.tobytes())==row['sourceHash']
            metadata=self.imp.table(row['game'],'gba/mid_index')[row['tileset']][str(row['id'])]
            assert metadata['behavior']==row['sourceBehavior']
            sources.append(dict(game=row['game'],pair=row['tileset'],id=row['id'],sourceHash=row['sourceHash'],sourceBehavior=metadata['behavior']))
        proof=super().validate();proof.update(actual_imported_source_rows_checked=len(sources),actual_imported_source_pixels_checked=len(sources)*256,actual_imported_mid_index_behaviors_checked=True)
        (self.out/'actual-source-validation.json').write_text(json.dumps(sources,indent=2));(self.out/'proof.json').write_text(json.dumps(proof,indent=2))
        return proof

    def reviewed_variants(self):
        # These complete R/S room surfaces and objects were independently
        # reviewed beside Emerald, not inferred from an equal numeric MID.
        hashes={
          ('building__dewford_gym',513):'a3e0d17da56a8060765c5b608f165ed8b5248f4180810be17b4987f7153eb83f',
          ('building__mauville_gym',514):'e59a8430f1c0ac01cd3063e467f467263c22b7a13d1e4f5a28a13e9340d34cf7',
          ('building__mauville_gym',521):'8dbd8546396dee8b53d62b66f4f665eaf812b1a1ab4f36a6fa92c994206647af',
          ('building__fortree_gym',514):'d8722f471026a76ada1f187c73bec5c80be023f554f78ff69dc1612bff10d959',
          ('building__generic_building',1022):'b852d7deb2cd28fda65340abb6fcd5d5af7a35bff785a36a2a575d2c2cb3cfe6',
          ('building__petalburg_gym',513):'1dc13b422a9d1001b67e2c702cabe9e160c4ee9ee9044b8c9b9c19f9a5c0d92a',
          ('building__sootopolis_gym',513):'17713f6c81158d5ec57e4817a1171132a31ab47d4829b6aaa0dc710319ce5f45',
          ('building__generic_building',528):'072ea9ecf641c592a19289253a3386d52ede5536ebfd6163c37aeb3987defe1a',
          ('building__generic_building',529):'74306f3331a63a7ae416c4573710e876fb06d38dc473fe70e467eb1e0f4f26f2',
          ('building__generic_building',580):'f19e43f774a19d9a042b73ce8125dfe5f83c5d0396365b3593e3b445ddc23e49'}
        records=[]
        for game in('ruby','sapphire'):
            for(pair,mid),expected in hashes.items():
                cell=self.scope[game][pair,mid];assert cell['pixel_sha256']==expected
                expected_behavior=101 if mid in(528,529)else 0
                assert cell['behavior']==expected_behavior
                self.independent_sources.add((game,pair,mid))
                records.append(dict(game=game,pair=pair,id=mid,sourceHash=expected,sourceBehavior=expected_behavior,
                    evidence='Independent whole-source review in held-variants-second-review.png and native source room: ordinary floor surface, complete two-cell entry rug, or backless household stool. Mossdeep slide-east arrows are explicitly excluded.'))
        self.contracts.append(dict(label='independently reviewed R/S variants',sources=records))

    def build(self):
        self.reviewed_variants()
        def existing_floor(pair,fallback):
            options=[r for r in self.prior if r['game']=='emerald'and r['style']=='gen2'and r['tileset']==pair and r.get('donor')and 'floor'in r['role']]
            return copy.deepcopy(options[0]['donor'])if options else fallback
        house=self.gb_ref('crystal','GUIDE_GENTS_HOUSE',15,0)
        clinic=self.gb_ref('crystal','CHERRYGROVE_POKECENTER_1F',4,0)
        mart=self.gb_ref('crystal','CHERRYGROVE_MART',43,0)
        school=existing_floor('building__pokemon_school',self.gb_at('crystal','EARLS_POKEMON_ACADEMY',0,4))
        floors=[('building__generic_building',553,house,'ordinary household carpet'),
                ('building__generic_building',545,house,'household floor with side-wall shadow'),
                ('building__pokemon_center',514,clinic,'public clinic floor'),
                ('building__shop',513,mart,'shop floor'),
                ('building__pokemon_school',513,school,'school classroom floor')]
        for pair,mid,donor,label in floors:
            self.aliases(pair,mid,self.native(donor,'reverse_gen2_hoenn_'+label.replace(' ','_')),
                'Actual complete native16px '+label+' counterpart, reviewed in the canonical source room beside Crystal. Native GB geometry remains1:1; source layout, collision, warps, actors and events remain unchanged.')
        wood=self.primitive('johto_domestic_stage_floor');stone=self.primitive('interior_saffrongym_floor')
        facility=self.primitive('johto_battle_lobby_floor');tile=self.primitive('interior_saffrongym_floor')
        tatami=self.primitive('johto_domestic_tatami_mat');casino=self.primitive('interior_gamecorner_floor');blue_tile=self.primitive('johto_gym_native_tiled_floor')
        for pair,mid,ref,material in[
            ('battle_arena',513,wood,'martial arena timber floor'),('battle_dome',515,facility,'battle-facility public floor'),
            ('battle_factory',513,stone,'factory stone floor'),('battle_frontier_ranking_hall',514,stone,'ranking-hall stone floor'),
            ('battle_palace',518,stone,'palace stone tiled floor'),('dewford_gym',513,wood,'martial gym timber floor'),
            ('fortree_gym',513,wood,'gym slatted timber floor'),('lilycove_museum',514,stone,'museum stone floor'),
            ('mauville_game_corner',514,casino,'casino carpet'),('mauville_gym',514,tile,'electric gym tiled walking floor'),
            ('mossdeep_game_corner',513,wood,'game-room timber floor'),('mossdeep_gym',513,tile,'teleporter gym tiled walking floor'),
            ('oceanic_museum',513,stone,'museum tiled walking floor'),('petalburg_gym',513,wood,'martial gym timber floor'),
            ('petalburg_gym',517,tatami,'gym woven mat floor'),('pokemon_day_care',513,house,'day-care carpet'),
            ('pokemon_fan_club',513,house,'fan-club carpet'),('pretty_petal_flower_shop',513,wood,'florist timber floor'),
            ('rustboro_gym',513,stone,'rock gym stone floor'),('sootopolis_gym',513,blue_tile,'ordinary blue gym tile floor')]:
            self.identical_family('building__'+pair,mid,self.native(ref,'reverse_gen2_hoenn_'+material.replace(' ','_')),
                'Visually reviewed complete native16px '+material+' surface. Uses the actual complete Crystal '+material+' counterpart at1:1, with the original Hoenn collision, teleporter/ice-puzzle state, encounters and all events retained. No functional switch, arrow, crack or inscription is inferred from floor color.')
        for pair,mids,ref,material in[
            ('battle_arena',[521],wood,'arena timber'),('battle_dome',[514,523],facility,'facility carpet'),
            ('pokemon_school',[515,516],school,'school tiles'),('pokemon_day_care',[514,517,518,519],house,'day-care carpet'),
            ('pokemon_fan_club',[514,515,516,517,518],house,'club carpet'),
            ('pretty_petal_flower_shop',[514,515,520,521,522,523],wood,'florist timber'),
            ('petalburg_gym',[518,525,526],tatami,'gym woven mat'),
            ('rustboro_gym',[514,515,516],stone,'gym ceramic tiles'),
            ('mossdeep_gym',[514,515,522,523,524],tile,'teleporter-gym ceramic tiles'),
            ('mossdeep_game_corner',[514,515,516,517,520],wood,'game-room timber'),
            ('mauville_gym',[515,521,522],tile,'electric-gym ceramic tiles'),
            ('oceanic_museum',[514,515],stone,'museum ceramic tiles'),('lilycove_museum',[515,521,522],stone,'museum ceramic tiles'),
            ('shop',list(range(514,528)),mart,'mart patterned tiles')]:
            for mid in mids:
                self.aliases('building__'+pair,mid,self.native(ref,'reverse_gen2_hoenn_'+material.replace(' ','_')),
                    'Independently reviewed full16px ordinary '+material+' floor variation in building-floor-candidates contacts and actual native room. The light/shaded pattern variants use one consistent complete native Crystal floor. Original source behavior is individually retained; functional switches, arrows, puzzle cracks and object panels are excluded from this explicit list.')
        wall=self.primitive('johto_house_full_wall')
        for mid in(533,541):self.identical_family('building__generic_building',mid,self.native(wall,'reverse_gen2_complete_classic_house_wall'),
            'Complete unadorned interior wall module. The original native Crystal striped wall repeats as a whole16px module to preserve Hoenn wall height; no window, clock, cupboard, ledge or door graphic is included in this source family.')
        # Whole native32x32 tables and16px padded stools share the original
        # source footprints. Exterior floor is removed from the complete GB
        # object before it is split into checked16px atlas cells.
        self.object_family('building__generic_building',[[590,591],[598,599]],'GUIDE_GENTS_HOUSE',(3,3),house,house,'complete household table')
        self.object_family('building__pokemon_center',[[573,574],[581,582]],'GUIDE_GENTS_HOUSE',(3,3),house,clinic,'complete clinic coffee table')
        bookcase=[[678,679],[686,687],[694,695]]
        book_hashes={'ruby':'91716d00bfb72b6f44b9298628cb9080f1d8d516cb07acb650efe345197da937','sapphire':'91716d00bfb72b6f44b9298628cb9080f1d8d516cb07acb650efe345197da937','emerald':'eba716d0f23b62aa4e81b6cd6aae9036782f6c4646e43f487173ca28215e6ee5'}
        for game in GAMES:
            whole=Image.new('RGBA',(32,48))
            for y,row in enumerate(bookcase):
                for x,mid in enumerate(row):
                    c=self.imp.cell_index(game)['building__generic_building',mid];ref=dict(game=game,tileset='building__generic_building',id=mid,hash=c['pixel_sha256']);whole.paste(preview.native_donor(self.cache,ref,self.packed),(x*16,y*16));self.independent_sources.add((game,'building__generic_building',mid))
            assert catalog.sha(whole.tobytes())==book_hashes[game],'Independently reviewed whole bookcase source changed'
        self.object_family('building__generic_building',bookcase,'GUIDE_GENTS_HOUSE',(0,0),house,house,'complete two-bay bookcase',
            row_pixels=[None]*8+list(range(32))+[None]*8,background_bands=[(0,8,wall),(8,40,house),(40,48,house)],
            source_bounds=[0,14,32,26],foot_anchor=39)
        clinic_wall=self.gb_at('crystal','AZALEA_POKECENTER_1F',3,0)
        for mid in(523,531):self.identical_family('building__pokemon_center',mid,self.native(clinic_wall,'reverse_gen2_complete_clinic_wall'),
            'Complete plain back-wall module, visually reviewed in the actual native clinic. Native Crystal clinic horizontal wall stripes remain1:1; the source has no cabinet, window, sign or clock.')
        clinic_front=self.gb_at('crystal','AZALEA_POKECENTER_1F',0,2)
        for mid in(517,545,605):self.identical_family('building__pokemon_center',mid,self.native(clinic_front,'reverse_gen2_complete_clinic_counter_front'),
            'Whole straight16px clinic counter front from native Crystal AZALEA_POKECENTER_1F x0,y2. Full cream top, blue trim and lower front remain intact1:1; distinct ball-storage side cabinets and terminal devices are not inferred from this straight plain module.')
        self.object_family('building__pokemon_center',[[546,547],[554,555]],'AZALEA_POKECENTER_1F',(0,0),clinic,[clinic_wall,clinic],'complete healing machine')
        self.object_family('building__pokemon_center',[[521],[529],[537]],'GUIDE_GENTS_HOUSE',(0,6),house,clinic,
            'complete clinic potted plant',row_pixels=[None]*12+list(range(32))+[None]*4,
            background_bands=[(0,32,clinic_wall),(32,48,clinic)],source_bounds=[0,11,16,33],foot_anchor=43)
        self.object_family('building__shop',[[549],[557]],'GUIDE_GENTS_HOUSE',(0,6),house,mart,'complete mart potted plant')
        # The48px source canvas includes wall above and floor below. Only the
        # actual21px window band repeats plain pane pixels; its sill stays39.
        self.object_family('building__generic_building',[[702,703],[710,711],[718,719]],'GUIDE_GENTS_HOUSE',(5,0),wall,wall,
            'complete two-pane household window',row_pixels=[None]*19+list(range(6))+list(range(6,11))+list(range(6,16))+[None]*8,
            column_pixels=list(range(16))*2,preserve_rects=[(1,19,14,21),(17,19,14,21)],
            background_bands=[(0,40,wall),(40,48,house)],source_bounds=[0,19,32,21],foot_anchor=39)
        self.primitive_cell('building__generic_building',523,self.primitive('johto_domestic_stairs_up'),house,'complete household ascending stairs',
            'Actual source warp contexts include RUSTBORO_FLAT2_1F to2F and2F to3F; the complete source is a16px ascending staircase, not a slatted door.')
        self.primitive_cell('building__generic_building',537,self.primitive('johto_shop_stairs_down'),house,'complete household descending stairs',
            'Actual source warp contexts include RUSTBORO_FLAT2_3F to2F and2F to1F, and COVE_LILY_MOTEL_2F to1F. The full native descending stair module is retained.')
        ruins=self.primitive('johto_ruins_native_tanoby_stone_floor')
        self.identical_family('building__battle_pyramid',653,self.native(ruins,'reverse_gen2_complete_pyramid_stone_floor'),
            'Actual native BattlePyramid Floor label0x28D, used by the reachable procedural square templates and the runtime Exit-to-Floor rewrite. Complete native Crystal Ruins stone floor remains1:1; source darkness/Flash, collision, random layout, exits and trainer/item events remain unchanged.')
        self.primitive_cell('building__battle_pyramid',654,self.primitive('kanto_saffron_complete_native_teleport_pad'),ruins,'complete pyramid exit warp pad',
            'Actual native BattlePyramid Exit label0x28E is the complete single16px glowing warp platform to the next floor. Uses the complete native Crystal teleport pad, not a walking floor or a hole; runtime exit behavior and procedural rewrites are untouched.')
        for mid,ref,label in[(571,tatami,'green maze floor'),(625,tatami,'green maze floor'),(775,tatami,'green lobby floor'),
                            (651,wood,'yellow maze floor'),(652,wood,'yellow maze floor'),(654,wood,'yellow maze floor'),
                            (707,blue_tile,'blue maze floor'),(711,blue_tile,'blue maze floor'),
                            (716,wood,'orange maze floor'),(717,wood,'orange maze floor'),
                            (741,facility,'purple maze floor'),(742,facility,'purple maze floor')]:
            self.identical_family('building__trainer_hill',mid,self.native(ref,'reverse_gen2_trainer_hill_'+label.replace(' ','_')),
                'Actual Trainer Hill procedural map MID was decoded from challenges[].floors[].map.metatiles +512, or the static lobby. This complete plain '+label+' was individually reviewed in the actual dynamic-source contact. Native Crystal whole floor module remains1:1; directional arrows, sound notes, healing machines, switches and wall/corner pieces are excluded. Original collision masks and challenge events stay native.')
        self.computers(dict(clinic=clinic,house=house,mart=mart,wood=wood,stone=stone,facility=facility,tatami=tatami,
                            gate=self.primitive('interior_gate_floor'),lab=existing_floor('building__lab',self.primitive('interior_lab_floor'))),clinic_wall)
        self.pc_caps(dict(clinic_wall=clinic_wall,facility_wall=self.primitive('johto_facility_back_wall'),house_wall=wall,
                         wood_wall=self.primitive('johto_facility_complete_horizontal_wall')))
        for mid,expected in CLINIC_FLOOR_CONTRACTS:
            assert self.imp.cell_index('emerald')['building__pokemon_center',mid]['pixel_sha256']==expected
            floor=self.gb_at('crystal','AZALEA_POKECENTER_1F',3,1)if mid==519 else clinic
            role='reverse_gen2_clinic_staff_floor'if mid==519 else'reverse_gen2_clinic_full_floor_variation'
            self.aliases('building__pokemon_center',mid,self.native(floor,role),
                'Independently reviewed complete clinic walking-floor/shadow variation in clinic-floor-candidates.png and the native1F/2F room. Literal source hash recorded in CLINIC_FLOOR_CONTRACTS; the color subset was only a contact-search aid. Complete native Crystal clinic floor remains1:1 and matches furniture bases. All Pokeball floor-logo fragments, devices, rails, seats and wall outlines are explicitly excluded.')
        self.televisions()
        self.clinic_rails()
        self.clinic_furnishings(house,clinic,clinic_wall)
        self.clinic_structure(clinic,clinic_wall)
        self.beds_tables(house,wood)
        self.generic_plants(dict(house=house,wood=wood,stone=stone),wall)
        self.rs_gym_variants(blue_tile)
        self.compact_decorations(house,wood)
        self.large_decor_desks(house,wood)
        self.secret_cave_perimeters()
        self.backed_chairs(dict(wood=wood,house=house,stone=stone))
        self.rs_mossdeep_symbols(blue_tile)
        self.object_family('general__facility',[[541]],'GUIDE_GENTS_HOUSE',(2,3),house,stone,'complete facility backless console stool')
        for game in('ruby','sapphire'):
            for mid in(512,513,514,515,516,517,525):
                if('building__battle_tower',mid)in self.scope[game]:
                    self.add(game,'building__battle_tower',mid,self.native(facility,'reverse_gen2_original_tower_lobby_floor'),
                        'Individually reviewed original R/S Battle Tower lobby plain/shaded blue floor in pc-nearby-floor-materials.png and the actual lobby context. Complete native Crystal Battle Tower lobby floor remains1:1, consistent with the equivalent Emerald Frontier lobby. All source hashes and behaviors are separately guarded; counters, terminals and the patterned floor logo are excluded.')
            for mid in(514,515):
                self.add(game,'building__rustboro_gym',mid,self.native(self.primitive('johto_facility_back_wall'),'reverse_gen2_rustboro_plain_back_wall'),
                    'Independently reviewed complete R/S rock-gym plain wall panels, including their actual north/west perimeter contexts in ruby-rustboro-wall-context.png. They are wall modules, unlike the unrelated Emerald floor at these MIDs. Uses a complete actual native Crystal facility back wall at1:1; window516 is a distinct feature and is excluded.')
            rug=self.imp.cell_index(game)['building__mauville_gym',515]
            assert rug['pixel_sha256']=='4eb37fc5bf58b5be6c0c3dd3dee99d597b2486e49937c7e9408ae90628c0b04a'and rug['behavior']==101
            self.add(game,'building__mauville_gym',515,self.native(self.primitive('johto_battle_entry_mat'),'reverse_gen2_complete_gym_entry_mat'),
                'Independently reviewed complete single16px R/S gym entrance rug, MB_SOUTH_ARROW_WARP101. Uses the whole original Crystal Battle Tower16px entry mat, with no clipped two-cell household rug and no floor replacement. Emerald515 is a distinct walking-floor motif and remains separately authored.')
        for pair,mids,ref in[
            ('building__battle_frontier',[513,514,515,516,517,525,952,953,960],facility),
            ('building__battle_arena',[514,515,522,523,524,525,526],stone),
            ('building__trainer_hill',[816,822],tatami),('building__trainer_hill',[817,823,825],wood),
            ('building__shop',[616,624,632,640,633],self.primitive('interior_gate_floor'))]:
            for mid in mids:self.aliases(pair,mid,self.native(ref,'reverse_gen2_complete_public_floor'),
                'Complete plain/shaded public-room floor independently reviewed beside the actual PC placement in all-native-rse-pc-contexts.png and pc-nearby-floor-materials.png. Native Crystal floor remains1:1 and matches the corresponding object base. Functional devices, counters, arrows and labels are excluded from the explicit source list.')
        for game in('ruby','sapphire'):
            for mid in(607,608,614,615):
                if('building__contest',mid)in self.scope[game]:self.add(game,'building__contest',mid,self.native(facility,'reverse_gen2_complete_contest_public_floor'),
                    'Actual R/S contest lobby carpet variants, individually reviewed in PC room-context and floor-material contacts. Uses a coherent complete native Crystal public-facility floor; all floor backgrounds on its reviewed computer use this same exact counterpart. No counter or wall glyph is inferred from carpet color.')
        self.surface_contracts(dict(house=house,wood=wood,stone=stone,facility=facility,tatami=tatami,blue_tile=blue_tile,clinic=clinic,
            wall_house=wall,wall_facility=self.primitive('johto_facility_back_wall'),ship=self.primitive('interior_shiproom_floor'),
            link=self.primitive('kanto_room_native_link_room_floor'),lab=existing_floor('building__lab',self.primitive('interior_lab_floor')),
            cave=self.gb_ref('crystal','UNION_CAVE_1F',2,0)))
        context_bases=dict(house=house,wood=wood,stone=stone,facility=facility,tatami=tatami,blue_tile=blue_tile,
            ship=self.primitive('interior_shiproom_floor'),link=self.primitive('kanto_room_native_link_room_floor'),
            mart=mart,casino=casino,ruins=ruins,wall_house=wall,wall_facility=self.primitive('johto_facility_back_wall'))
        for pair,mid,expected,material in CONTEXT_SURFACE_CONTRACTS:
            assert self.imp.cell_index('emerald')[pair,mid]['pixel_sha256']==expected,('Room-context reviewed source surface changed',pair,mid)
            self.aliases(pair,mid,self.native(context_bases[material],'reverse_gen2_context_reviewed_'+material),
                'The full actual native room and adjacent5x5 source cells were independently reviewed in hotspot-contexts-02 and context-surface-reviewed-decisions.json. This is an ordinary complete '+material.replace('_',' ')+' module, not a furniture/window/rail fragment, directional symbol or water/ice tile. The matching whole original Crystal module stays1:1, with native source collision, warp/encounter/overhead behavior and all map/NPC positions unchanged. The literal pair/MID/full RGBA hash binds this decision; contact ranks never determine identity.')
        self.contracts.append(dict(label='complete room-context surface review',sources=[dict(pair=p,id=m,sourceHash=h,material=k)for p,m,h,k in CONTEXT_SURFACE_CONTRACTS],source_contexts='hotspot-contexts-02.json',reviewed_decisions='context-surface-reviewed-decisions.json',contacts=['hotspot-contexts-02-'+str(i).zfill(2)+'.png'for i in range(1,7)],pixel_scale=1))
        self.shared_secondary_surfaces()
        # Entries were independently reviewed in the actual native room maps.
        for pair,mids,gbmap,coords,base,label in[
            ('building__generic_building',[528,529],'GUIDE_GENTS_HOUSE',[(2,7),(3,7)],house,'complete entry rug'),
            ('building__generic_building',[580],'GUIDE_GENTS_HOUSE',[(2,3)],house,'complete backless household stool'),
            ('building__pokemon_center',[564],'CHERRYGROVE_POKECENTER_1F',[(7,5)],clinic,'complete padded clinic seat')]:
            for mid,xy in zip(mids,coords):
                self.object_family(pair,[[mid]],gbmap,xy,base,base,label)
        # Native black atlas canvases use a real complete black Crystal cell.
        # This exact-pixel identity never changes invisible/puzzle behavior.
        black=None
        for name in('FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN','TEAM_ROCKET_BASE_B1F','GOLDENROD_UNDERGROUND'):
            m=self.imp.table('crystal','maps').get(name)
            if not m:continue
            for y in range(m['height']*2):
                for x in range(m['width']*2):
                    ref=self.gb_at('crystal',name,x,y)
                    if ref['hash']==catalog.sha(Image.new('RGBA',(16,16),(0,0,0,255)).tobytes()):
                        black=ref;black['monochrome']=True;black['palettes']=[[[255,255,255],[170,170,170],[85,85,85],[0,0,0]]for _ in range(8)];break
                if black:break
            if black:break
        self.preserved=[]
        opaque_black=catalog.sha(Image.new('RGBA',(16,16),(0,0,0,255)).tobytes())
        transparent_black=catalog.sha(Image.new('RGBA',(16,16),(0,0,0,0)).tobytes())
        for game in GAMES:
            for(pair,mid),cell in self.scope[game].items():
                if(game,'gen2',pair,mid,None)in self.occupied:continue
                if cell['pixel_sha256']==transparent_black:
                    self.preserved.append(dict(game=game,pair=pair,id=mid,sourceHash=cell['pixel_sha256'],reason='Fully transparent native canvas remains alpha0; no opaque black replacement is authored.'));continue
                if cell['pixel_sha256']==opaque_black:
                    if not black:
                        self.preserved.append(dict(game=game,pair=pair,id=mid,sourceHash=cell['pixel_sha256'],reason='Identical black/transparent native background remains black in every theme; no object, room floor or functional art is omitted.'));continue
                    self.add(game,pair,mid,self.native(black,'reverse_gen2_exact_black_canvas'),
                        'Complete native source canvas and actual Crystal neutral black glyph are exactly opaque black16x16. Only this all-black glyph uses its original monochrome pixels, avoiding the global58-gray DAY palette tint; strict donor hashes and every pixel are checked. This preserves unused/camera-border canvases or concealed puzzle cells and their exact source behavior; no semantic guess or palette fallback.')
        held={}
        for item in self.held:
            key=item.get('game'),'gen2',item.get('pair'),item.get('id'),None
            if key not in self.rows:held.setdefault((key,item['reason']),item)
        self.held=list(held.values())

    def aliases(self,pair,mid,art,evidence):
        canonical=self.imp.cell_index('emerald').get((pair,mid))
        if not canonical or(pair,mid)not in self.scope['emerald']:return
        if canonical['pixel_sha256']in(catalog.sha(Image.new('RGBA',(16,16),(0,0,0,255)).tobytes()),catalog.sha(Image.new('RGBA',(16,16)).tobytes())):return
        for game in GAMES:
            actual_pair='general__ship'if pair=='general__inside_ship'and game in('ruby','sapphire')else pair
            cell=self.scope[game].get((actual_pair,mid))
            if not cell:continue
            independent=(game,actual_pair,mid)in self.independent_sources
            if not independent and(cell.get('behavior')!=canonical.get('behavior')or native_geometry(self,game,actual_pair,mid)!=native_geometry(self,'emerald',pair,mid)):
                self.held.append(dict(game=game,pair=actual_pair,id=mid,reason='Canonical RSE indexed-layer geometry or behavior differs; needs separate source review.'));continue
            selected=self.prepare_art(game,actual_pair,mid,art)
            self.add(game,actual_pair,mid,selected,evidence+(' Native R/S and Emerald artwork differs; the complete source family was independently compared in the recorded variant/whole-object contract. Every per-cell source hash and behavior remain individually guarded.'if independent else' Cross-cartridge alias requires the same exact source family/MID, complete indexed-layer geometry (including transparency), and behavior; full source RGBA is separately fingerprinted. R/S general__ship is the explicit counterpart bank of Emerald general__inside_ship; all other aliases retain their exact pair name.'))

    def prepare_art(self,game,pair,mid,art):
        selected=copy.deepcopy(art)
        exact_source=selected.pop('_sourceOverMask',False)
        if '_objectMask'in selected or exact_source:
            cell=self.imp.cell_index(game)[pair,mid];silhouette=selected.pop('_objectMask','0'*256);ref=dict(game=game,tileset=pair,id=mid,hash=cell['pixel_sha256'])
            preview.native_donor(self.cache,ref,self.packed);mids,palette,layers=self.packed[game,pair];slot=mids.index(mid)
            over=catalog.rgba_native(layers['over'][slot*256:(slot+1)*256],palette,True)if'over'in layers else Image.new('RGBA',(16,16))
            selected['overMask']=''.join('1'if p[3]else'0'for p in over.get_flattened_data())if exact_source else silhouette if over.getchannel('A').getbbox()else'0'*256
        return selected

    def computers(self,bases,wall):
        families={'pokemon_center':([540,548,694],'clinic'),'contest':([597],'facility'),'shop':([613],'gate'),
                  'battle_tower':([641],'facility'),'pokemon_day_care':([523],'house'),'lab':([630],'lab'),
                  'battle_frontier':([641,951],'facility'),'battle_arena':([656],'stone'),
                  'trainer_hill':([778],'tatami'),'mossdeep_game_corner':([560],'wood')}
        hashes={'2845b5c65066c27fe281ed652c3904753cbeb5ca4fe4ddb1a416ec06eecb8eb1','2d907e267e8ccacfd85b0a01289603ebcf59faf78a6d5d32486be005e9c6b42a',
          '3da78020ab72ccf0730c3ceab612c453cdca44fa85e91dd1955a86baaf512a3e','3ea20960a18ef8bbc65b700dc6179675f6bf303e1e0efed5170b7f784c02f882',
          '437a5f1aab26a5708c835222a620f0979257258a9f56b2fec9ab572aa946b832','49b797f6eba78b4c041762450072d597f9b9432476a9065b4be1123d9e13b744',
          '5696c6539ff139fc4a7488293586f6ee3bc94f9332cd0e6367f6e757cd21b268','6baa4a1f9bfe14d364dcedc6ba9db9ae015d62e8a4bcbbb0be6e4ea575c7cc71',
          '72e8647fc2d6a20cb2ac0ab21f3ee52204b7158976d307f78bf23ec6004d1058','930e280442fee8340e43a4345a7df6336eccff09a3ec43ce54dc0e15ce207f46',
          'c5b4bf71c755e9be7515a21140f8d382fd4555562a213c4410c46bc8795143f5'}
        for game in GAMES:
            for suffix,(bottoms,material)in families.items():
                pair='building__'+suffix
                for bottom in bottoms:
                    if(pair,4)not in self.scope[game]or(pair,bottom)not in self.scope[game]:continue
                    whole=Image.new('RGBA',(16,32))
                    for y,mid in enumerate((4,bottom)):
                        c=self.imp.cell_index(game)[pair,mid];whole.paste(preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed),(0,y*16))
                    fingerprint=catalog.sha(whole.tobytes());assert fingerprint in hashes,('Whole independently reviewed PC family changed',game,pair,bottom)
                    self.object_family(pair,[[4],[bottom]],'CHERRYGROVE_POKECENTER_1F',(9,0),wall,bases[material],
                        'complete computer',row_pixels=list(range(8,32))+[None]*8,preserve_rects=[(0,0,16,24)],
                        background_bands=[(0,24,wall),(24,32,bases[material])],source_bounds=[0,0,16,24],foot_anchor=23,only_game=game)
                    self.contracts.append(dict(label='independent complete PC source',game=game,pair=pair,ids=[4,bottom],wholeSourceHash=fingerprint,
                        source_contact='all-native-rse-pc-families.png',native_context_contact='all-native-rse-pc-contexts.png',base_material=material,
                        source_visible_bounds=[0,0,16,24],classic_native_source_bounds=[0,8,16,24],foot_anchor=23,pixel_scale=1))

    def pc_caps(self,materials):
        cap=self.gb_at('crystal','VIOLET_MART',2,4)
        palettes=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['VIOLET_MART'],'DAY')
        clinic=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['AZALEA_POKECENTER_1F'],'DAY')
        cap['palettes']=copy.deepcopy(palettes);cap['palettes'][5]=copy.deepcopy(clinic[3])
        materials.update(partition_cap=cap,counter_return=self.primitive('johto_casino_service_counter_left_corner'))
        for game,pair,mid,expected,kind in PC_CAP_CONTRACTS:
            cell=self.imp.cell_index(game)[pair,mid];assert cell['pixel_sha256']==expected
            if kind=='curtain_header':
                self.held.append(dict(game=game,pair=pair,id=mid,sourceHash=expected,reason='Whole source includes a blue curtain pelmet above the PC cap. A plain wall would erase the curtain; retain until its whole native Crystal curtain-header equivalent is reviewed.',possible_equivalent='Native complete stage/curtain pelmet with the PC cap removed; preserve the original upper decorative strip.'));continue
            role='reverse_gen2_complete_pc_'+kind
            art=self.native(materials[kind],role)
            if kind in('partition_cap','counter_return'):art['_objectMask']='1'*256;art=self.prepare_art(game,pair,mid,art)
            self.add(game,pair,mid,art,'All actual PC placements were independently reviewed with the ABOVE cell included, not just the two lower body cells. The small native G3 cap is removed because the complete24px native Crystal computer is already foot-anchored in the next two cells. '+('This cell is a genuine '+kind.replace('_',' ')+', retained with a complete actual native Crystal counter module rather than erased as wall.'if kind in('partition_cap','counter_return')else'The ordinary room wall/header is replaced with the coherent complete native Crystal '+kind.replace('_',' ')+'.')+' This cartridge source has its own full RGBA guard; all PC interactions, physical positions and neighboring counters/devices stay native.')
        self.contracts.append(dict(label='all PC above-cell source review',sources=[dict(game=g,pair=p,id=m,sourceHash=h,kind=k)for g,p,m,h,k in PC_CAP_CONTRACTS],source_context='../tileshift-reverse-gen2-pc-cap-source-review/all25-above-cells-reviewed.json',physical_pc_foot_anchor_unchanged=True))

    def surface_contracts(self,materials):
        for pair,mid,expected,material in SURFACE_CONTRACTS:
            source=self.imp.cell_index('emerald')[pair,mid];assert source['pixel_sha256']==expected,('Reviewed surface source changed',pair,mid)
            structural=material.startswith('wall_')
            self.aliases(pair,mid,self.native(materials[material],'reverse_gen2_reviewed_'+material+'_surface'),
                'Complete unadorned '+('interior wall/cap'if structural else'interior walking-floor')+' module independently reviewed in surface-hotspots-reviewed-01.png and the actual native source room. The literal pair/MID and full RGBA fingerprint are recorded in SURFACE_CONTRACTS, so ranking/contact positions cannot change its identity. Uses the complete matching native Crystal '+material+' module at1:1. Source warps, collisions, indoor/cave encounters, secret-base customization and all room events remain unchanged. Column shafts, ornaments, stairs, logos, water and directional puzzle panels are excluded from this explicit surface list.')
        self.contracts.append(dict(label='reviewed frequent native surfaces',source_contact='surface-hotspots-reviewed-01.png',stable_source_contracts=[dict(pair=p,id=m,sourceHash=h,material=k)for p,m,h,k in SURFACE_CONTRACTS],pixel_scale=1))

    def shared_secondary_surfaces(self):
        # These explicit native secondary banks occur with two primary-bank
        # choices. Only whole plain surfaces are shared, never object halves.
        banks={'contest','battle_tent','battle_palace','battle_frontier','facility'};copied=[]
        prior=[r for r in self.prior if r['game']in GAMES and r['style']=='gen2']
        for row in list(self.rows.values())+prior:
            pair=row['tileset'];mid=row['id'];game=row['game']
            if mid<512 or pair.split('__',1)[-1]not in banks or not pair.startswith(('building__','general__')):continue
            if not any(s in row['role']for s in('floor','surface','plain_back_wall','complete_clinic_wall')):continue
            other=('general__'if pair.startswith('building__')else'building__')+pair.split('__',1)[1]
            target=self.scope[game].get((other,mid));source=self.imp.cell_index(game).get((pair,mid))
            if not target or not source or target['pixel_sha256']!=source['pixel_sha256']or target['behavior']!=source['behavior']:continue
            if native_geometry(self,game,other,mid)!=native_geometry(self,game,pair,mid):continue
            art={k:copy.deepcopy(v)for k,v in row.items()if k not in{'game','style','tileset','id','map','sourceHash','sourceBehavior','status','evidence','compositionPixelHash'}}
            self.add(game,other,mid,art,'Complete native surface from the same explicitly named secondary '+pair.split('__',1)[1]+' bank used with a different primary bank. This alias requires exact full RGBA, all indexed planes including transparency, behavior and MID within the same cartridge. Only previously reviewed plain floor/wall surface roles are eligible; furniture halves, devices, water and puzzle features are excluded. '+row.get('evidence',''))
            copied.append(dict(game=game,source_pair=pair,target_pair=other,id=mid,sourceHash=target['pixel_sha256'],behavior=target['behavior'],role=row['role']))
        self.contracts.append(dict(label='exact shared secondary plain surfaces',aliases=copied))

    def televisions(self):
        # Guide Gent's TV occupies y12..23; the cabinet below is a separate
        # object. Retain the whole screen/frame and repeat4 plain screen rows.
        ys=list(range(12,18))+list(range(16,20))+list(range(18,24));parts=[]
        for y,sy in enumerate(ys):parts+=self.gb_rect('crystal','GUIDE_GENTS_HOUSE',32,sy,16,1,0,y)
        art=self.composite(None,parts,'reverse_gen2_complete_household_television');art['_objectMask']='1'*256
        canonical=self.imp.cell_index('emerald')['building__generic_building',2]
        for game in GAMES:
            for(pair,mid),cell in self.scope[game].items():
                if mid!=2 or not pair.startswith('building__'):continue
                if cell['behavior']!=canonical['behavior']or cell['pixel_sha256']!=canonical['pixel_sha256']or native_geometry(self,game,pair,mid)!=native_geometry(self,'emerald','building__generic_building',2):continue
                self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),
                    'Complete native Crystal television screen/frame, separate from the cabinet beneath it, at1:1 pixels. Four plain screen rows repeat to fit the original16px Hoenn TV footprint without resizing or dropping the frame. Shared BUILDING primary-TV aliases require the same MID, exact complete RGBA, indexed planes and television behavior. Source interaction and positions remain unchanged.')
        self.contracts.append(dict(label='complete television',source_pair='building__generic_building',source_id=2,source_bounds=[0,0,16,16],classic_source_bounds=[32,12,16,12],classic_source_rows=ys,pixel_scale=1))

    def clinic_rails(self):
        stem=self.gb_at('crystal','VIOLET_MART',2,1);cap=self.gb_at('crystal','VIOLET_MART',2,4)
        palettes=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['VIOLET_MART'],'DAY')
        clinic=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['AZALEA_POKECENTER_1F'],'DAY')
        # The whole cap's upper stem uses native grayscale slot1. Only its
        # lower front's tan slot6 changes to the actual clinic blue slot4.
        cap['palettes']=copy.deepcopy(palettes);cap['palettes'][5]=copy.deepcopy(clinic[3])
        ball=self.gb_at('crystal','AZALEA_POKECENTER_1F',2,2)
        for top,bottom in[(592,600),(593,601)]:
            upper=self.composite(stem,[dict(donor=ball,srcX=0,srcY=0,w=8,h=3,x=4,y=13)],'reverse_gen2_complete_clinic_storage_stem')
            lower=self.composite(cap,[dict(donor=ball,srcX=0,srcY=3,w=8,h=5,x=4,y=0)],'reverse_gen2_complete_clinic_storage_cap')
            for mid,art in((top,upper),(bottom,lower)):
                art['_objectMask']='1'*256
                self.aliases('building__pokemon_center',mid,art,
                    'Complete32px vertical Ball-storage counter assembled from original native Crystal cream16px vertical stem, its complete lower front cap, and one complete8px stored-Poke-Ball glyph. The actual VIOLET_MART x2,y1/x2,y4 rail has no device or terminal. Only the lower cap uses literal native AZALEA_POKECENTER blue front palette; upper cream/gray border pixels stay unchanged. The whole8px ball glyph straddles the cell boundary without resizing/cropping; source positions, healer behavior and collision are unchanged.')
        wall=self.gb_at('crystal','AZALEA_POKECENTER_1F',3,0)
        for mid in(584,585):
            art=self.composite(wall,[dict(donor=stem,srcX=0,srcY=0,w=16,h=8,x=0,y=8)],'reverse_gen2_clinic_storage_upper_rail')
            art['_objectMask']='0'*128+'1'*128
            self.aliases('building__pokemon_center',mid,art,'The native Ball-storage counter stem begins8px into this upper wall cell. Native Crystal plain cream/gray stem bands continue into the two lower counter cells, exposing matching clinic wall above. This removes the complete native side stand header while retaining its original40px visible stem/front height, lower foot anchor, and native ball glyph.')
        self.contracts.append(dict(label='complete clinic Ball-storage side counters',source_families=[[[584],[592],[600]],[[585],[593],[601]]],native_stem=stem,native_lower_cap=cap,native_ball=ball,ball_rectangle=[0,0,8,8],ball_destination=[4,29],pixel_scale=1,canvas=[16,48],visible_bounds=[0,8,16,40],foot_anchor=47))

    def whole_program(self,pair,layout,parts,base,label,skip_ids=(),preserve_source_over=False):
        width,height=len(layout[0])*16,len(layout)*16
        assert all(len(row)*16==width for row in layout)
        for part in parts:assert 0<=part['x']<part['x']+part['w']<=width and 0<=part['y']<part['y']+part['h']<=height
        for row,ids in enumerate(layout):
            for column,mid in enumerate(ids):
                if mid in skip_ids:continue
                left,top=column*16,row*16;selected=[];mask=[False]*256
                for part in parts:
                    x,y=max(left,part['x']),max(top,part['y']);right,bottom=min(left+16,part['x']+part['w']),min(top+16,part['y']+part['h'])
                    if right<=x or bottom<=y:continue
                    selected.append(dict(donor=part['donor'],srcX=part.get('srcX',0)+x-part['x'],srcY=part.get('srcY',0)+y-part['y'],w=right-x,h=bottom-y,x=x-left,y=y-top))
                    for yy in range(y-top,bottom-top):
                        for xx in range(x-left,right-left):mask[yy*16+xx]=True
                background=base[row]if isinstance(base,list)else base
                role='reverse_gen2_'+label.replace(' ','_')
                if len(selected)>32:selected=self.visible_program_parts(selected)
                assert len(selected)<=32,('Whole native program part limit',label,mid,len(selected))
                art=self.composite(background,selected,role)if selected else self.native(background,role)
                art['_objectMask']=''.join('1'if v else'0'for v in mask)
                if preserve_source_over:art['_sourceOverMask']=True
                self.aliases(pair,mid,art,'Whole source '+label+' family '+str(layout)+' reviewed together. Uses complete original Crystal furnishing/frame modules or an explicitly authored native-color counterpart at1:1; splitting the final atlas program across source16px cells never removes any frame, feet, labels or controls. Exterior uses the exact selected room wall/floor. Source positions, collision, actors, interaction and scripts stay native.')
        self.contracts.append(dict(label=label,pair=pair,source_ids=layout,whole_canvas=[width,height],complete_native_parts=parts,pixel_scale=1))

    def visible_program_parts(self,parts):
        # GB source rectangles are opaque. Fully covered pixels can be omitted
        # from earlier ordinary background/rail bands without changing the
        # final image or splitting the last complete furnishing/icon module.
        original=self.render(self.composite(None,parts,'private_uncompacted_program'))
        covered=[False]*256;visible=[]
        for p in reversed(parts):
            donor=self.gb_image(p['donor']);assert all(donor.getpixel((x,y))[3]==255 for y in range(p.get('srcY',0),p.get('srcY',0)+p['h'])for x in range(p.get('srcX',0),p.get('srcX',0)+p['w']))
            mask=[False]*256
            for y in range(p['y'],p['y']+p['h']):
                for x in range(p['x'],p['x']+p['w']):
                    if not covered[y*16+x]:mask[y*16+x]=True;covered[y*16+x]=True
            for r in runs(mask):visible.append(dict(donor=p['donor'],srcX=p.get('srcX',0)+r['x']-p['x'],srcY=p.get('srcY',0)+r['y']-p['y'],w=r['w'],h=r['h'],x=r['x'],y=r['y']))
        assert self.render(self.composite(None,visible,'private_visible_program')).tobytes()==original.tobytes(),'Native program compaction changed pixels'
        return visible

    def clinic_furnishings(self,house,clinic,wall):
        pair='building__pokemon_center'
        contexts=[]
        for game in GAMES:
            for name,spec in self.imp.table(game,'gba/native/manifest')['layouts'].items():
                if spec['pair']!=pair:continue
                layout=decode_layout(self.cache/game/'data/generated/gba/native'/spec['file']);w,h=layout['width'],layout['height']
                for index,mid in enumerate(layout['mids']):
                    if mid!=617:continue
                    x,y=index%w,index//w
                    found=[[layout['mids'][(y+dy)*w+x+dx]if y+dy<h and x+dx<w else None for dx in range(2)]for dy in range(3)]
                    assert found==[[617,618],[625,626],[633,634]],('Stock cabinet upper wall is used in a different context',game,name,x,y,found)
                    contexts.append(dict(game=game,map=name,x=x,y=y,source_ids=found))
        self.contracts.append(dict(label='all clinic stock-cabinet header contexts',contexts=contexts,reserved_upper_ids=[617,618],native_body_height=32,native_foot_anchor=39,pixel_scale=1))
        for game,label,layout,expected in CLINIC_OBJECT_SOURCE_CONTRACTS:
            whole=Image.new('RGBA',(len(layout[0])*16,len(layout)*16))
            for y,row in enumerate(layout):
                for x,mid in enumerate(row):
                    c=self.imp.cell_index(game)[pair,mid];whole.paste(preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed),(x*16,y*16))
                    self.independent_sources.add((game,pair,mid))
            assert catalog.sha(whole.tobytes())==expected,('Whole clinic source changed',game,label)
        self.object_family(pair,[[617,618],[625,626],[633,634]],'GUIDE_GENTS_HOUSE',(0,0),house,wall,
            'complete clinic stock bookcase',row_pixels=[None]*8+list(range(32))+[None]*8,
            floor_zones=[(0,36,32,4)],background_bands=[(0,40,wall),(40,48,clinic)],
            source_bounds=[0,15,32,25],foot_anchor=39)
        chart=self.primitive('johto_complete_native_region_map')
        self.whole_program(pair,[[525,526],[533,534]],[dict(donor=chart,srcX=1,srcY=1,w=14,h=12,x=9,y=11)],wall,'complete clinic region chart')
        parts=self.gb_rect('crystal','GUIDE_GENTS_HOUSE',32,12,16,12,0,0)
        for part in parts:part['y']+=12
        for sy,height in((8,16),(24,8)):
            body=self.gb_rect('crystal','CHERRYGROVE_POKECENTER_1F',144,sy,16,height,0,0)
            for part in body:part['x']+=16;part['y']+=20+sy-8
            parts+=body
        orange=self.native_color_brushes('AZALEA_POKECENTER_1F',4)[2]
        parts +=[dict(donor=orange,srcX=0,srcY=0,w=5,h=1,x=22,y=27),dict(donor=orange,srcX=0,srcY=0,w=1,h=5,x=24,y=25)]
        staff=self.gb_at('crystal','AZALEA_POKECENTER_1F',3,1)
        self.whole_program(pair,[[586,587],[594,595],[519,603]],parts,[wall,wall,staff],'complete clinic display and healing control',skip_ids=(519,))
        self.object_family(pair,[[515,516]],'GUIDE_GENTS_HOUSE',(2,7),house,clinic,'complete clinic entry rug')
        self.object_family('building__generic_building',[[520,521]],'GUIDE_GENTS_HOUSE',(2,7),house,house,'complete alternate household entry rug')
        self.clinic_floor_emblem(clinic)
        palettes=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['AZALEA_POKECENTER_1F'],'DAY')
        self.object_family(pair,[[550]],'CHERRYGROVE_POKECENTER_1F',(7,5),clinic,clinic,'complete pink clinic padded seat',
            donor_palettes=[copy.deepcopy(palettes[1])for _ in range(8)],source_bounds=[0,0,16,16],foot_anchor=15)

    def native_color_brushes(self,map_id,slot):
        blank=self.gb_ref('crystal','VIOLET_MART',0,0)
        assert set(self.neutral(blank).get_flattened_data())=={(0,0,0,255)}
        palette=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')[map_id],'DAY')[slot]
        refs=[]
        for color in palette:
            ref=copy.deepcopy(blank);ref['palettes']=[[list(color)for _ in range(4)]for _ in range(8)];refs.append(ref)
        return refs

    def clinic_structure(self,clinic,wall):
        pair='building__pokemon_center';gray=self.native_color_brushes('AZALEA_POKECENTER_1F',0)
        for game,mid,expected,behavior in CLINIC_STRUCTURE_SOURCE_CONTRACTS:
            c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==expected and c['behavior']==behavior,('Complete clinic structure source changed',game,mid)
        black=self.gb_ref('crystal','VIOLET_MART',0,0);black['monochrome']=True
        black['palettes']=[[[255,255,255],[170,170,170],[85,85,85],[0,0,0]]for _ in range(8)]
        orange={(222,123,49,255),(247,181,115,255),(255,230,181,255)}
        cap={(255,255,255,255),(148,148,148,255)};edge={(82,82,107,255)}
        for mid in(520,527,528,535,536,543,552,567):
            c=self.imp.cell_index('emerald')[pair,mid];source=preview.native_donor(self.cache,dict(game='emerald',tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed)
            assert all(p[3]==255 for p in source.get_flattened_data()),'These reviewed corner sources are opaque, including exact black void'
            pixels=list(source.get_flattened_data());parts=[];object_mask=[False]*256
            if mid in(520,527,528,535):
                base=wall;groups=[(black,[p==(0,0,0,255)for p in pixels],False),(gray[0],[p in cap for p in pixels],True)]
                object_mask=[p!=(0,0,0,255)for p in pixels]
            elif mid in(536,543):
                base=clinic;groups=[(wall,[p in orange for p in pixels],True),(gray[3],[p in cap|edge for p in pixels],True)]
            else:base=clinic;groups=[(black,[p==(0,0,0,255)for p in pixels],False)]
            for donor,mask,structural in groups:
                for r in runs(mask):
                    parts.append(dict(donor=donor,srcX=r['x']if donor==wall else 0,srcY=r['y']if donor==wall else 0,w=r['w'],h=r['h'],x=r['x'],y=r['y']))
                if structural:object_mask=[a or b for a,b in zip(object_mask,mask)]
            assert len(parts)<=32,('Clinic wall contour parts',mid,len(parts))
            art=self.composite(base,parts,'reverse_gen2_complete_clinic_handed_wall_corner')if parts else self.native(base,'reverse_gen2_complete_clinic_handed_wall_corner')
            art['_objectMask']=''.join('1'if b else'0'for b in object_mask)
            art['_sourceOverMask']=True
            self.aliases(pair,mid,art,'The actual complete clinic wall/room-cutaway corner was independently reviewed in the source room, excluding522 and other plant-containing composite cells. A purpose-built correctly handed contour uses whole original Crystal gray wall/floor texture planes plus literal native cream/dark trim, with source exact opaque-black exterior triangles preserved. Only plain structural wall surfaces are masked to their known contour; no object, rail, sign, plant or floor rectangle is inferred from color. Source native collision, all source positions and actors remain unchanged.')
        self.clinic_stair_frame(clinic)
        over=[]
        for game,mid,expected,behavior in CLINIC_STRUCTURE_SOURCE_CONTRACTS:
            row=self.rows.get((game,'gen2',pair,mid,None))
            if mid==517 or row is None:continue
            mids,palette,layers=self.packed[game,pair];slot=mids.index(mid)
            native=catalog.rgba_native(layers['over'][slot*256:(slot+1)*256],palette,True)if'over'in layers else Image.new('RGBA',(16,16))
            mask=''.join('1'if p[3]else'0'for p in native.get_flattened_data())
            assert row['overMask']==mask,'Clinic native stair/wall over-priority mask changed'
            over.append(dict(game=game,id=mid,native_over_mask=mask))
        self.contracts.append(dict(label='clinic structural source and actor-depth proof',sources=[dict(game=g,id=m,sourceHash=h,sourceBehavior=b)for g,m,h,b in CLINIC_STRUCTURE_SOURCE_CONTRACTS],exact_native_over_masks=over,black_corner_pixels_remain_opaque_black=True,positions_collision_and_warps_unchanged=True))

    def rs_mossdeep_symbols(self,floor):
        for game,mid,expected,behavior,direction in MOSSDEEP_SYMBOL_SOURCE_CONTRACTS:
            pair='building__mossdeep_gym';c=self.imp.cell_index(game)[pair,mid]
            assert c['pixel_sha256']==expected and c['behavior']==behavior,('Actual R/S directional gym panel changed',game,mid)
            art,proof=classic_floor_symbol(self,floor,direction)
            self.add(game,pair,mid,art,'Independently reviewed complete native R/S Mossdeep directional panel, with the actual original behavior label and visible arrow direction. Uses a purpose-built original-Crystal-style8px '+direction+' arrow and contrast pad over the whole exact native gym floor; source directional walking/sliding semantics, collision, source layout, NPC positions and scripts remain unchanged. No unrelated Emerald floor is aliased by numeric MID.')
            self.contracts.append(dict(label='known R/S Mossdeep directional panel',game=game,source_id=mid,sourceHash=expected,sourceBehavior=behavior,direction=direction,classic_symbol=proof,semantic_source='actual Ruby metatile_behaviors byId table and native glyph, Sapphire runtime uses Ruby constants'))

    def clinic_stair_frame(self,clinic):
        pair='building__pokemon_center';layout=[[640,641],[648,649],[656,657]];source=Image.new('RGBA',(32,48))
        for y,row in enumerate(layout):
            for x,mid in enumerate(row):
                c=self.imp.cell_index('emerald')[pair,mid];source.paste(preview.native_donor(self.cache,dict(game='emerald',tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed),(x*16,y*16))
        floors=set()
        for mid in(514,541,542,549,551,559):
            c=self.imp.cell_index('emerald')[pair,mid];floors.update(preview.native_donor(self.cache,dict(game='emerald',tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed).get_flattened_data())
        foreground_by_row=[sum(source.getpixel((x,y))not in floors for x in range(32))for y in range(48)]
        assert max(y for y,n in enumerate(foreground_by_row)if n)==40,'Native clinic stair frame foot anchor changed'
        gray=self.native_color_brushes('AZALEA_POKECENTER_1F',0);red=self.native_color_brushes('AZALEA_POKECENTER_1F',1)[2]
        stair=self.primitive('johto_shop_stairs_up');parts=[]
        for cy,row in enumerate(layout):
            for cx,mid in enumerate(row):
                pixels=[source.getpixel((cx*16+x,cy*16+y))for y in range(16)for x in range(16)]
                tread_colors={(82,82,107,255),(148,148,148,255),(148,148,165,255)}
                tread=[pixels[y*16+x]in tread_colors and 8<=cy*16+y<=36 for y in range(16)for x in range(16)]
                groups=[(gray[1],[p not in floors for p in pixels],False),
                    (gray[3],[p in{(255,99,49,255),(156,115,90,255)}or(p==(82,82,107,255)and not tread[i])for i,p in enumerate(pixels)],False)]
                for donor,mask,texture in groups:
                    for r in runs(mask):parts.append(dict(donor=donor,srcX=r['x']if texture else 0,srcY=r['y']if texture else 0,w=r['w'],h=r['h'],x=cx*16+r['x'],y=cy*16+r['y']))
                # Repeat only the native ordinary8px tread surface; all outer
                # source handrail contours and the full original icon remain.
                for r in runs(tread):
                    yy=r['y']
                    while yy<r['y']+r['h']:
                        hh=min(r['y']+r['h']-yy,8-yy%8)
                        parts.append(dict(donor=stair,srcX=r['x'],srcY=4+yy%8,w=r['w'],h=hh,x=cx*16+r['x'],y=cy*16+yy))
                        yy+=hh
        # Complete original16px upward-stair icon, fully inside the source
        # stair flight and overlapping the original left/middle warp cell.
        parts.append(dict(donor=stair,srcX=0,srcY=0,w=16,h=16,x=0,y=12))
        self.whole_program(pair,layout,parts,clinic,'purpose-built complete clinic ascending stair frame',preserve_source_over=True)
        self.contracts.append(dict(label='whole clinic upward stairs',source_ids=layout,canvas=[32,48],source_foot_anchor=40,
            floor_only_rows=[41,47],source_structural_pixels_by_row=foreground_by_row,whole_native_stair_icon=stair,whole_icon_destination=[0,12,16,16],
            native_plain_tread_source_rectangle=[0,4,16,8],source_over_masks_preserved_exactly=True,source_warp_and_positions_unchanged=True,pixel_scale=1))

    def clinic_floor_emblem(self,clinic):
        # A new full native-palette floor emblem, not an enlarged16px sprite.
        # Its52px circle, complete band and button are authored directly on
        # the actual64x64 floor canvas, in native1px steps. The four upper
        #620..623 cells contain the circle tip as well as counter shadow.
        brushes=self.native_color_brushes('AZALEA_POKECENTER_1F',1)
        pixels=[None]*(64*64)
        for y in range(64):
            for x in range(64):
                r=(x-31.5)**2+(y-31.5)**2
                if r>26**2:continue
                color=3 if r>25**2 else 2 if y<32 else 0
                if 30<=y<=33:color=3
                button=(x-31.5)**2+(y-31.5)**2
                if button<=7**2:color=3 if button>5**2 else 0
                pixels[y*64+x]=color
        parts=[]
        for cy in range(4):
            for cx in range(4):
                for color,donor in enumerate(brushes):
                    mask=[pixels[(cy*16+y)*64+cx*16+x]==color for y in range(16)for x in range(16)]
                    parts +=[dict(donor=donor,srcX=0,srcY=0,w=r['w'],h=r['h'],x=cx*16+r['x'],y=cy*16+r['y'])for r in runs(mask)]
        layout=[[620,621,622,623],[560,561,562,563],[568,569,570,571],[576,577,578,579]]
        self.whole_program('building__pokemon_center',layout,parts,clinic,'purpose-built complete clinic floor Pokeball emblem')
        self.contracts.append(dict(label='purpose-built native-palette clinic floor emblem',source_ids=layout,canvas=[64,64],circle_diameter=52,whole_band_and_button=True,native_palette_map='AZALEA_POKECENTER_1F',native_palette_slot=2,pixel_scale=1,no_resized_sprite=True))

    def beds_tables(self,house,wood):
        pair='building__generic_building';ship='FAST_SHIP_CABINS_NNW_NNE_NE'
        for game,label,layout,expected in TABLE_SOURCE_CONTRACTS:
            whole=Image.new('RGBA',(len(layout[0])*16,len(layout)*16))
            for y,row in enumerate(layout):
                for x,mid in enumerate(row):
                    c=self.imp.cell_index(game)[pair,mid];whole.paste(preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed),(x*16,y*16))
                    self.independent_sources.add((game,pair,mid))
            assert catalog.sha(whole.tobytes())==expected,('Whole independently reviewed table variant changed',game,label)
        self.contracts.append(dict(label='independent RSE table motifs',source_contact='table-rse-independent-variants.png',sources=[dict(game=g,label=n,source_ids=ids,wholeSourceHash=h)for g,n,ids,h in TABLE_SOURCE_CONTRACTS],semantic_review='R/S and Emerald differ in the complete table surface/cloth design but retain the same whole table meaning and footprint, original mug/plain variants, full frame and feet. Native Crystal counterparts are the complete module families, not numeric-ID aliases.'))
        self.object_family(pair,[[723,724],[731,732]],ship,(7,1),self.gb_at('crystal',ship,0,5),wood,
            'complete single bed',column_pixels=list(range(16))+[None]*16,preserve_rects=[(0,0,16,32)],
            source_bounds=[0,0,20,29],foot_anchor=[28,31])
        for layout in([ [744,745,746],[752,753,754] ],[ [744,745,745,746],[752,753,753,754] ]):
            repeats=len(layout[0])-2;columns=list(range(16))+list(range(8,24))*repeats+list(range(16,32))
            self.object_family(pair,layout,'GUIDE_GENTS_HOUSE',(3,3),house,wood,'complete large household table',column_pixels=columns,
                source_bounds=[0,0,len(layout[0])*16,32],foot_anchor=31)
        floor=self.gb_at('crystal',ship,0,5)
        clear_cup=dict(dest=[8,8,8,8],source=[16,8]);move_cup=dict(dest=[20,8,8,8],source=[8,8])
        self.object_family(pair,[[584,585],[592,593]],ship,(2,5),floor,wood,'complete dining table with mug',
            pixel_overrides=[clear_cup,move_cup],source_bounds=[0,0,32,32],foot_anchor=31)
        self.object_family(pair,[[584,606],[592,593]],ship,(2,5),floor,wood,'complete plain dining table',
            pixel_overrides=[clear_cup],source_bounds=[0,0,32,32],foot_anchor=31)
        self.contracts.append(dict(label='bed/table whole-source review',source_contact='../tileshift-reverse-gen2-bed-table-source-review/whole-native-features.png',
            source_contexts='../tileshift-reverse-gen2-bed-table-source-review/contexts.json',native_counterparts='../tileshift-reverse-gen2-bed-table-source-review/ship-correct-counterparts.png',
            bed_complete_native_dimensions=[16,32],bed_source_visible_dimensions=[20,29],bed_full_canvas=[32,32],bed_foot_extension_within_existing_canvas=3,
            mug_original_rectangle=[8,8,8,8],mug_destination=[20,8],mug_original_patch_fill=[16,8,8,8],pixel_scale=1))

    def generic_plants(self,bases,wall):
        pair='building__generic_building';house=self.gb_ref('crystal','GUIDE_GENTS_HOUSE',15,0)
        for game,top,bottom,expected,material in PLANT_CONTRACTS:
            whole=Image.new('RGBA',(16,32))
            for y,mid in enumerate((top,bottom)):
                c=self.imp.cell_index(game)[pair,mid];whole.paste(preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed),(0,y*16))
            assert catalog.sha(whole.tobytes())==expected,('Complete plant source changed',game,top,bottom)
            background=[(0,8,wall),(8,32,bases[material])]if top in(656,660)else None
            self.object_family(pair,[[top],[bottom]],'GUIDE_GENTS_HOUSE',(0,6),house,bases[material],
                'complete domestic potted tree',background_bands=background,source_bounds=[0,0,16,32],foot_anchor=31,only_game=game)
            self.contracts.append(dict(label='complete potted-tree source',game=game,pair=pair,ids=[top,bottom],wholeSourceHash=expected,
                source_contact='generic-complete-plant-families.png',material=material,source_foot_anchor=31,classic_foot_anchor=31,
                context_evidence='Both adjacent Rustboro plants838/839 use the same actual gray-tiled floor, including its source shadow variation. Route119/Sootopolis back-wall plants656/660 retain wall above the8px floor line; other plants use their actual room floor.',pixel_scale=1))

    def rs_gym_variants(self,floor):
        wall=self.primitive('johto_facility_back_wall');cap=self.primitive('johto_facility_complete_horizontal_wall')
        shaft=self.primitive('johto_facility_complete_vertical_wall');base=self.primitive('johto_facility_complete_wall_lower_end')
        statue=self.primitive('facility_complete_original_violet_compact_statue')
        for game,pair,mid,expected,kind in RS_SPECIAL_GYM_CONTRACTS:
            assert self.imp.cell_index(game)[pair,mid]['pixel_sha256']==expected
            if kind=='window':
                art=self.composite(wall,self.gb_rect('crystal','NEW_BARK_TOWN',232,72,16,8,0,6),'reverse_gen2_rs_complete_gym_slit_window')
                evidence='The actual R/S north wall uses four complete single16px slit windows, not halves of a32px frame. Uses the entire original16x8 Crystal New Bark house window at native1:1, inside the original16px wall cell; the full frame and glass shading remain intact over the selected native GSC wall.'
            else:
                ref=statue if kind=='compact_statue'else floor if kind=='floor'else wall if kind=='wall'else cap if kind=='top_cap'else base if kind in('base','footer')else shaft
                art=self.native(ref,'reverse_gen2_rs_gym_'+kind)
                evidence=('The R/S entrance statue is a complete single16px bust/plinth. Original Crystal VIOLET_GYM51q0 is a complete compact16px gym statue, with its whole frame and highlights; no32px statue head or foot is cropped.'if kind=='compact_statue'else
                    'Actual R/S Lavaridge B1F has three structural256px partition posts:521,529,twelve537,545,553. Complete original GSC cap/vertical shaft/lower-base modules form the full original16px width and256px height; only the plain shaft repeats. The553base and neighboring526/527 strip are structural footer, not ordinary floor; full base/footer art stays present. Ordinary514/515 walking floor is separately mapped to the native GSC gym floor, and520is an actual plain wall. No door, opening or warp is invented in the post family.')
            self.add(game,pair,mid,art,evidence+' Exact source hash and native behavior are independently guarded for this cartridge; source layout, collision, NPCs and scripts are untouched.')
        self.contracts.append(dict(label='source-specific R/S gym architecture',source_context='../tileshift-reverse-gen2-rs-gym-source-review/rs-specific-contexts.json',column_bounds_evidence='../tileshift-reverse-gen2-rs-gym-source-review/rs-column-native-bounds.json',column_source_ids=[521,529]+[537]*12+[545,553],column_native_size=[16,256],source_profiles=[dict(game=g,pair=p,id=m,sourceHash=h,kind=k)for g,p,m,h,k in RS_SPECIAL_GYM_CONTRACTS],pixel_scale=1))

    def backed_chairs(self,bases):
        donor=self.gb_ref('crystal','EARLS_POKEMON_ACADEMY',22,2)
        east=[dict(donor=donor,srcX=2,srcY=3,w=12,h=6,x=3,y=6),
            dict(donor=donor,srcX=2,srcY=3,w=3,h=12,x=1,y=1),
            dict(donor=donor,srcX=2,srcY=11,w=2,h=4,x=3,y=12),
            dict(donor=donor,srcX=12,srcY=11,w=2,h=4,x=12,y=12),
            dict(donor=donor,srcX=3,srcY=9,w=10,h=2,x=4,y=11)]
        west=[dict(donor=p['donor'],srcX=p['srcX']+i,srcY=p['srcY'],w=1,h=p['h'],x=15-p['x']-i,y=p['y'])for p in east for i in range(p['w'])]
        for game,mid,expected,facing,material in BACKED_CHAIR_SOURCE_CONTRACTS:
            pair='building__generic_building';assert self.imp.cell_index(game)[pair,mid]['pixel_sha256']==expected
            parts=east if facing=='east'else west;mask=[False]*256
            for p in parts:
                for y in range(p['y'],p['y']+p['h']):
                    for x in range(p['x'],p['x']+p['w']):mask[y*16+x]=True
            art=self.composite(bases[material],parts,'reverse_gen2_complete_backed_chair_'+facing);art['_objectMask']=''.join('1'if v else'0'for v in mask)
            self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),
                'The actual complete source chair and adjacent table/context were independently reviewed for this cartridge in backed-chair-source-contexts. The source backrest is on the '+('left, facing the table to its east'if facing=='east'else'right, facing the table to its west')+'. Uses an approved purpose-built Crystal side view assembled from complete original native seat-panel, vertical back/post, apron and leg modules. Legs remain downward; the opposite view reflects source columns horizontally, never rotates a chair. Whole16px footprint, original facing, NPC positions and behavior remain unchanged; only verified exterior floor is replaced by the exact '+material+' room floor.')
        self.contracts.append(dict(label='complete correctly facing native-module side chairs',sources=[dict(game=g,id=m,sourceHash=h,facing=f,material=k)for g,m,h,f,k in BACKED_CHAIR_SOURCE_CONTRACTS],source_contexts='backed-chair-source-contexts.json',prototype='purpose-built-gen2-side-chairs-prototype.png',east_native_parts=east,west_is_exact_horizontal_reflection=True,pixel_scale=1,positions_and_npc_facing_unchanged=True,explicit_nonchair_exclusions=[557,735]))

    def secret_cave_perimeters(self):
        # Handedness was checked against the actual entire native red-cave2
        # grid, not inferred from lighter/darker contact colors. Floor522 is
        # inside the room;528..531 are outside wall backing.
        shapes={513:(14,3),514:(12,3),515:(12,2),521:(6,3),523:(4,2),517:(4,0),519:(6,1)}
        for bank in('red_cave','blue_cave','brown_cave','yellow_cave'):
            pair='secret_base__secret_base_'+bank
            for mid,(block,quadrant)in shapes.items():
                self.aliases(pair,mid,self.native(self.gb_ref('crystal','UNION_CAVE_1F',block,quadrant),'reverse_gen2_secret_cave_complete_handed_wall'),
                    'The complete actual native Secret Base room perimeter was reviewed in secret-base-static-'+bank+' and independently checked against the red-cave2 grid.513 has solid mass NW/open room SE,514 has room south,515 mass NE/room SW,521 room east,523 room west,517 mass SE/open room NW,519 mass SW/open room NE. The entire correctly handed original Crystal CAVE module is retained1:1 and joins the exact native522 walking floor. Outside backing528..531 is not interpreted as raised floor. Native collision, entrances, decorations and source placement stay unchanged.')
            mass=self.gb_ref('crystal','UNION_CAVE_1F',4,3)
            parts=[dict(donor=mass,srcX=0,srcY=0,w=8,h=8,x=x,y=y)for y in(0,8)for x in(0,8)]
            for mid in(528,529,530,531):
                self.aliases(pair,mid,self.composite(None,parts,'reverse_gen2_secret_cave_solid_backing'),
                    'Actual native Secret Base cell is exterior wall-mass backing outside the traversable room, not its522 walking floor. Four whole original8px Crystal cave rock-top texture modules repeat at1:1, with no wall/front corner accidentally repeated through this solid backing. Every source hash and source behavior is guarded; no native room geometry or decoration state changes.')
        self.contracts.append(dict(label='Secret Base cave handed perimeter',source_grids='secret-base-static-*-EM_SECRET_BASE_*',source_ids={str(m):dict(block=b,quadrant=q)for m,(b,q)in shapes.items()},floor=522,outside_backing=[528,529,530,531],held_internal_step_corners=[525,527],native_backing_module=dict(block=4,quadrant=3,rectangle=[0,0,8,8]),pixel_scale=1))

    def compact_decorations(self,house,wood):
        compact=list(range(8))+list(range(24,32));ball=self.pokeball_motif()
        definitions={r['game']:{d['name']:d for d in r['definitions']}for r in self.decorations}
        palette=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['AZALEA_POKECENTER_1F'],'DAY')
        def color(index):return [copy.deepcopy(palette[index])for _ in range(8)]
        for game,pair,name,did,mid,expected in COMPACT_DECOR_SOURCE_CONTRACTS:
            label=name.lower().replace('é','e')
            definition=definitions[game][name]
            assert definition['id']==did and definition['shape']==[1,1]and definition['metatiles']==[mid]
            assert definition['permission']==(0 if name.endswith('DESK')else 1)and not definition['top_row_wall_variants']
            assert self.imp.cell_index(game)[pair,mid]['pixel_sha256']==expected,('Whole compact furnishing source changed',game,pair,name)
            floor=wood if pair.endswith('_tree')else self.gb_ref('crystal','UNION_CAVE_1F',2,0)
            if name.endswith('DESK'):
                self.object_family(pair,[[mid]],'GUIDE_GENTS_HOUSE',(3,3),house,floor,'purpose-built complete compact '+label,
                    row_pixels=compact,column_pixels=compact,pixel_overrides=[dict(dest=[3,2,10,6],source=[12,8])],
                    floor_zones=[(0,12,16,4)],additional_parts=ball if name.startswith('POKéMON')else(),
                    source_cutout_zones=[(0,0,16,8)]if name.startswith('POKéMON')else(),only_game=game,
                    source_bounds=[0,0,16,16],foot_anchor=15)
            elif name in('SMALL CHAIR','POKéMON CHAIR','COMFORT CHAIR'):
                self.object_family(pair,[[mid]],'GUIDE_GENTS_HOUSE',(2,3),house,floor,'complete backless '+label,
                    additional_parts=ball if name.startswith('POKéMON')else(),only_game=game,source_bounds=[0,0,16,16],foot_anchor=15,
                    donor_palettes=color(2)if name=='COMFORT CHAIR'else None)
            elif name in('HEAVY CHAIR','PRETTY CHAIR','BRICK CHAIR'):
                index={'HEAVY CHAIR':0,'PRETTY CHAIR':3,'BRICK CHAIR':5}[name];parts=[]
                if name=='BRICK CHAIR':
                    brick=copy.deepcopy(self.gb_at('crystal','WILLS_ROOM',0,16));brick['palettes']=color(5)
                    parts=[dict(donor=brick,srcX=0,srcY=0,w=8,h=8,x=4,y=3)]
                self.object_family(pair,[[mid]],'CHERRYGROVE_POKECENTER_1F',(7,5),house,floor,'complete backless '+label,
                    donor_palettes=color(index),additional_parts=parts,only_game=game,source_bounds=[0,0,16,16],foot_anchor=15)
            elif name=='RAGGED CHAIR':
                self.object_family(pair,[[mid]],'GUIDE_GENTS_HOUSE',(3,3),house,floor,'purpose-built complete plank stool',
                    row_pixels=compact,column_pixels=compact,pixel_overrides=[dict(dest=[3,2,10,6],source=[12,8])],floor_zones=[(0,12,16,4)],
                    additional_parts=[dict(donor=self.primitive('johto_domestic_stage_floor'),srcX=0,srcY=0,w=8,h=8,x=4,y=1)],only_game=game,source_bounds=[0,0,16,16],foot_anchor=15)
            elif name in('CAMP CHAIR','HARD CHAIR'):
                parts=self.native_log_stool_parts()if name=='CAMP CHAIR'else self.native_stone_seat_parts()
                mask=[False]*256
                for p in parts:
                    for y in range(p['y'],p['y']+p['h']):
                        for x in range(p['x'],p['x']+p['w']):mask[y*16+x]=True
                art=self.composite(floor,parts,'reverse_gen2_complete_'+label.replace(' ','_'));art['_objectMask']=''.join('1'if v else'0'for v in mask)
                self.add(game,pair,mid,self.prepare_art(game,pair,mid,art),
                    'The actual definition and whole16px native source identify a '+('log stump seat'if name=='CAMP CHAIR'else'stone boulder seat')+'. Uses '+('a purpose-built complete log top/rings/cylinder/base in literal original Crystal wood colors'if name=='CAMP CHAIR'else'the complete native Crystal cave-boulder silhouette with the original clinic gray four-shade palette')+' at native1:1 pixels. No backrest or rotated feet are invented; exact floor remains behind the complete silhouette. Source placement, sitting behavior, collision and NPCs stay unchanged.')
            else:raise AssertionError(('Unreviewed compact furnishing',name))
            self.contracts.append(dict(label='actual defined compact decoration',game=game,pair=pair,name=name,decoration_id=did,
                source_id=mid,wholeSourceHash=expected,source_definition=definition,source_contact='compact-decor-all-source-'+str(GAMES.index(game)+1).zfill(2)+'.png',
                counterpart='Approved complete original8px table corner/apron/leg modules with native plain central wood panel'if name.endswith('DESK')else{
                    'SMALL CHAIR':'Original complete native Crystal backless round stool',
                    'POKéMON CHAIR':'Original complete round stool with purpose-built whole Pokeball emblem',
                    'HEAVY CHAIR':'Original complete padded seat/plinth in literal native gray metal colors',
                    'PRETTY CHAIR':'Original complete padded seat/plinth in literal native blue colors',
                    'COMFORT CHAIR':'Original complete round stool in literal native green colors',
                    'RAGGED CHAIR':'Purpose-built complete native corner/apron/leg modules with whole native plank surface',
                    'BRICK CHAIR':'Original complete pad/plinth with whole original brick8px surface in native earth colors',
                    'CAMP CHAIR':'Purpose-built complete log ring/cylinder/base in literal native wood colors',
                    'HARD CHAIR':'Complete original Crystal cave-boulder silhouette in literal native gray colors'}[name],
                emblem='Purpose-built complete native-color Pokeball circle/band/button'if name.startswith('POKéMON')else None,
                source_npc_and_placement_unchanged=True,pixel_scale=1))

    def large_decor_desks(self,house,wood):
        definitions={r['game']:{d['name']:d for d in r['definitions']}for r in self.decorations}
        palette=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['AZALEA_POKECENTER_1F'],'DAY')
        def color(index):return[copy.deepcopy(palette[index])for _ in range(8)]
        for game,pair,name,did,shape,ids,expected,behaviors in LARGE_DESK_SOURCE_CONTRACTS:
            definition=definitions[game][name];assert definition['id']==did and definition['permission']==0 and definition['shape']==list(shape)and definition['metatiles']==list(ids)
            w,h=shape;width,height=w*16,h*16;assert w==3 and h in(2,3)
            layout=[list(ids[y*w:(y+1)*w])for y in range(h)];whole=Image.new('RGBA',(width,height));actual_behaviors=[]
            for y,row in enumerate(layout):
                for x,mid in enumerate(row):
                    c=self.imp.cell_index(game)[pair,mid];actual_behaviors.append(c['behavior'])
                    whole.paste(preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed),(x*16,y*16))
            assert catalog.sha(whole.tobytes())==expected and tuple(actual_behaviors)==tuple(behaviors),('Whole defined large-desk source changed',game,pair,name)
            rows=list(range(32))if h==2 else list(range(16))+list(range(8,16))*2+list(range(16,32))
            columns=list(range(16))+list(range(8,24))+list(range(16,32))
            tint={'HEAVY DESK':0,'COMFORT DESK':2,'PRETTY DESK':3,'BRICK DESK':5,'HARD DESK':0}.get(name)
            if name=='HEAVY DESK':material=self.native_color_brushes('AZALEA_POKECENTER_1F',0)[1];sx=sy=0
            elif name=='PRETTY DESK':material=self.native_color_brushes('AZALEA_POKECENTER_1F',3)[1];sx=sy=0
            elif name=='COMFORT DESK':material=self.gb_at('crystal','GUIDE_GENTS_HOUSE',0,6);sx=sy=4
            elif name=='BRICK DESK':material=copy.deepcopy(self.gb_at('crystal','WILLS_ROOM',0,16));material['palettes']=color(5);sx=sy=0
            elif name=='HARD DESK':material=copy.deepcopy(self.gb_ref('crystal','UNION_CAVE_1F',2,0));material['palettes']=color(0);sx=sy=0
            else:material=self.primitive('johto_domestic_stage_floor');sx=sy=0
            parts=[dict(donor=material,srcX=sx,srcY=sy,w=8,h=8,x=x,y=y)for y in range(8,height-8,8)for x in range(8,40,8)]
            floor=wood if pair.endswith('_tree')else self.gb_ref('crystal','UNION_CAVE_1F',2,0)
            self.object_family(pair,layout,'GUIDE_GENTS_HOUSE',(3,3),house,floor,'complete native-module '+name.lower(),
                row_pixels=rows,column_pixels=columns,floor_zones=[(0,height-4,width,4)],additional_parts=parts,
                donor_palettes=color(tint)if tint is not None else None,only_game=game,source_bounds=[0,0,width,height],foot_anchor=height-1)
            self.contracts.append(dict(label='whole defined large decoration desk',game=game,pair=pair,name=name,decoration_id=did,
                definition=definition,wholeSourceHash=expected,source_behaviors=behaviors,source_native_dimensions=[width,height],
                source_review='../tileshift-reverse-gen2-large-desk-source-review/all18banks-body-review.json',
                approved_prototype='complete-native-large-desk-counterparts-prototypes.png',complete_frame_caps_apron_legs_once=True,
                repeated_plain_native_rows=[8,15]if h==3 else None,source_foot_and_native_foot=height-1,
                only_bounded_checker_between_feet_removed=True,pixel_scale=1))

    def native_log_stool_parts(self):
        brushes=self.native_color_brushes('AZALEA_POKECENTER_1F',5)
        rectangles=[(2,2,6,12,9),(3,2,6,1,9),(3,13,6,1,9),(3,2,14,12,1),(1,5,8,1,6),(1,10,8,1,6)]
        rectangles +=[(3,x,y,w,h)for x,y,w,h in[(5,1,6,1),(3,2,10,1),(2,3,12,1),(1,4,14,2),(2,6,12,1),(3,7,10,1),(5,8,6,1)]]
        rectangles +=[(0,x,y,w,h)for x,y,w,h in[(4,2,8,1),(3,3,10,1),(2,4,12,2),(3,6,10,1),(4,7,8,1)]]
        rectangles +=[(1,x,y,w,h)for x,y,w,h in[(5,3,6,1),(4,4,1,2),(11,4,1,2),(5,6,6,1)]]
        return[dict(donor=brushes[c],srcX=0,srcY=0,w=w,h=h,x=x,y=y)for c,x,y,w,h in rectangles]

    def native_stone_seat_parts(self):
        rock=copy.deepcopy(self.gb_ref('crystal','VICTORY_ROAD',24,0))
        palette=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['AZALEA_POKECENTER_1F'],'DAY')[0]
        rock['palettes']=[copy.deepcopy(palette)for _ in range(8)]
        spans=[(6,5),(4,8),(3,10),(2,12),(1,14),(1,14),(1,15)]+[(0,16)]*7+[(1,15),(2,11)];mask=[False]*256
        for y,(x,w)in enumerate(spans):
            for xx in range(x,x+w):mask[y*16+xx]=True
        return[dict(donor=rock,srcX=r['x'],srcY=r['y'],w=r['w'],h=r['h'],x=r['x'],y=r['y'])for r in runs(mask)]

    def pokeball_motif(self):
        # A new ordinary Pokeball emblem for modern decor without a direct
        # Crystal furnishing. Four literal native Crystal colors, no resized
        # GBA art and no clipped statue/pedestal masquerading as a chair.
        blank=self.gb_ref('crystal','VIOLET_MART',0,0)
        assert set(self.neutral(blank).get_flattened_data())=={(0,0,0,255)}
        palette=preview.palette_set(self.imp.table('crystal','palettes'),self.imp.table('crystal','maps')['AZALEA_POKECENTER_1F'],'DAY')[1]
        refs=[]
        for color in palette:
            ref=copy.deepcopy(blank);ref['palettes']=[[list(color)for _ in range(4)]for _ in range(8)];refs.append(ref)
        white,pink,red,black=refs
        def part(ref,x,y,w,h):return dict(donor=ref,srcX=0,srcY=0,w=w,h=h,x=x,y=y)
        spans=[(6,4),(4,8),(3,10),(2,12),(2,12),(1,14),(1,14),(1,14),(1,14),(1,14),(2,12),(3,10),(4,8),(6,4)]
        silhouette=[False]*256
        for y,(x,w)in enumerate(spans):
            for xx in range(x,x+w):silhouette[y*16+xx]=True
        native_orb=self.primitive('johto_gym_complete_statue_head')
        parts=[dict(donor=native_orb,srcX=s['x'],srcY=s['y'],w=s['w'],h=s['h'],x=s['x'],y=s['y'])for s in runs(silhouette)]
        mask=[False]*256
        for y in range(7,13):
            x,w=spans[y]
            for xx in range(x+1,x+w-1):mask[y*16+xx]=True
        parts +=[part(white,s['x'],s['y'],s['w'],s['h'])for s in runs(mask)]
        parts +=[part(black,2,6,12,2),part(black,6,5,4,4),part(white,7,6,2,2)]
        assert len(parts)<=16
        self.contracts.append(dict(label='purpose-built Gen2 Pokeball furnishing emblem',kind='new_native_palette_program',dimensions=[16,16],visible_circle=[1,0,14,14],literal_crystal_colors=palette,native_color_context='AZALEA_POKECENTER_1F DAY palette2',functional_marks_preserved=['complete circular outline','red upper shell','white lower shell','dark equatorial band','white center button'],pixel_scale=1,no_gba_pixels_recolored=True))
        return parts

    def identical_family(self,pair,mid,art,evidence):
        canonical=self.imp.cell_index('emerald').get((pair,mid))
        if not canonical or(pair,mid)not in self.scope['emerald']:return
        for(p,m),candidate in self.scope['emerald'].items():
            if pair=='building__pokemon_center'and m in(617,618)and m!=mid:continue
            if p!=pair or candidate['pixel_sha256']!=canonical['pixel_sha256']or candidate.get('behavior')!=canonical.get('behavior'):continue
            if native_geometry(self,'emerald',pair,m)!=native_geometry(self,'emerald',pair,mid):continue
            self.aliases(pair,m,art,evidence+' Any additional same-pair cell must have identical complete native RGBA, all indexed layer geometry and behavior to this explicitly reviewed source; IDs alone never imply equivalence.')

    def primitive_cell(self,pair,mid,ref,base,label,evidence):
        # Exterior neutral-white is actual empty background in these reviewed
        # stair/warp modules. Enclosed pale steps, rails and highlights stay.
        ts=self.imp.table('crystal','tilesets')[ref['tileset']];sheet=Image.open(self.cache/'crystal'/ts['image']).convert('RGBA')
        block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));neutral=preview.native_cell(sheet,ts,block,ref['quadrant'])
        assert catalog.sha(neutral.tobytes())==ref['hash']
        outside=exterior(neutral,{(255,255,255,255)})
        mask=[(x,y)not in outside for y in range(16)for x in range(16)]
        parts=[dict(donor=ref,srcX=s['x'],srcY=s['y'],w=s['w'],h=s['h'],x=s['x'],y=s['y'])for s in runs(mask)]
        assert parts and len(parts)<=32
        art=self.composite(base,parts,'reverse_gen2_hoenn_'+label.replace(' ','_'));art['_objectMask']=''.join('1'if value else'0'for value in mask)
        self.aliases(pair,mid,art,evidence+' Complete actual native Crystal16px '+label+' at1:1. Only connected empty exterior background is rebased to the actual room floor; the entire step/rail/pad silhouette and enclosed highlights stay intact. Source positions, collision, warp targets and actors remain unchanged.')
        self.contracts.append(dict(pair=pair,source_id=mid,label=label,donor=ref,retained_native_pixels=sum(mask),pixel_scale=1))

    def object_family(self,pair,layout,gbmap,origin,source_floor,target_floor,label,row_pixels=None,column_pixels=None,preserve_rects=(),background_bands=None,source_bounds=None,foot_anchor=None,only_game=None,pixel_overrides=(),floor_zones=None,donor_palettes=None,additional_parts=(),source_cutout_zones=()):
        width,height=len(layout[0])*16,len(layout)*16;assert all(len(row)*16==width for row in layout)
        for part in additional_parts:
            assert 0<=part['x']<part['x']+part['w']<=width and 0<=part['y']<part['y']+part['h']<=height
            assert 0<=part.get('srcX',0)<part.get('srcX',0)+part['w']<=16 and 0<=part.get('srcY',0)<part.get('srcY',0)+part['h']<=16
        ys=row_pixels or list(range(height));xs=column_pixels or list(range(width));assert len(ys)==height and len(xs)==width
        ox,oy=origin[0]*16,origin[1]*16;image=self.imp.gb('crystal',gbmap)[0];whole=Image.new('RGBA',(width,height));coordinates=[[None]*width for _ in range(height)]
        for y,sy in enumerate(ys):
            if sy is not None:
                for x,sx in enumerate(xs):
                    if sx is not None:coordinates[y][x]=(ox+sx,oy+sy)
        for patch in pixel_overrides:
            x,y,w,h=patch['dest'];sx,sy=patch['source']
            for yy in range(h):
                for xx in range(w):coordinates[y+yy][x+xx]=(ox+sx+xx,oy+sy+yy)
        for y in range(height):
            for x in range(width):
                if coordinates[y][x]is not None:whole.putpixel((x,y),image.getpixel(coordinates[y][x]))
        outside=exterior(whole,set(self.gb_image(source_floor).get_flattened_data()))
        for x,y,w,h in preserve_rects:outside.difference_update((xx,yy)for yy in range(y,y+h)for xx in range(x,x+w))
        explicit_contour=None
        if gbmap=='GUIDE_GENTS_HOUSE'and origin==(2,3)and width==height==16:
            # The top/beside floor checker inherits the stool's palette, so
            # colored floor equality alone cannot identify its background.
            explicit_contour={}
            for y,x,w in[(5,5,6),(6,3,10)]+[(y,2,12)for y in range(7,15)]:explicit_contour[y]=(x,w)
            keep={(x,y)for y,(a,w)in explicit_contour.items()for x in range(a,a+w)}
            keep.update((x,15)for x in(3,4,5,10,11,12))
            outside={(x,y)for y in range(16)for x in range(16)}-keep
        elif gbmap=='CHERRYGROVE_POKECENTER_1F'and origin==(7,5)and width==height==16:
            # Complete padded seat/plinth/shadow; only its four upper-corner
            # floor pixels are omitted. White seat highlights stay inside.
            explicit_contour={0:(2,12),1:(1,14),**{y:(0,16)for y in range(2,16)}}
            keep={(x,y)for y,(a,w)in explicit_contour.items()for x in range(a,a+w)}
            outside={(x,y)for y in range(16)for x in range(16)}-keep
        bounded_floor=[];pink_seeds=[]
        # These original neutral checker pixels are room floor even where an
        # enclosing furniture8px tile applies the brown furniture palette.
        # Explicit lower-foot zones keep all tops, aprons, frames and legs.
        zones=[]
        if gbmap=='GUIDE_GENTS_HOUSE'and origin==(3,3):zones=[(0,28,width,4)]
        elif label=='complete two-bay bookcase':zones=[(0,36,width,4)]
        elif gbmap=='FAST_SHIP_CABINS_NNW_NNE_NE'and origin==(2,5):zones=[(0,27,width,5)]
        if floor_zones is not None:zones=list(floor_zones)
        if zones:
            neutral=Image.new('RGBA',(width,height))
            for y in range(height):
                for x in range(width):
                    if coordinates[y][x]is not None:
                        sx,sy=coordinates[y][x];ref=self.gb_at('crystal',gbmap,sx//16,sy//16);neutral.putpixel((x,y),self.neutral(ref).getpixel((sx%16,sy%16)))
            for zx,zy,zw,zh in zones:
                for light,dark in((255,170),(170,85)):
                    for phase in(0,1):
                        matching={(x,y)for y in range(zy,zy+zh)for x in range(zx,zx+zw)if neutral.getpixel((x,y))==((light,light,light,255)if(x+y+phase)%2==0 else(dark,dark,dark,255))}
                        seeds=set()
                        for y in range(zy,zy+zh-1):
                            for x in range(zx,zx+zw-1):
                                patch={(x,y),(x+1,y),(x,y+1),(x+1,y+1)}
                                if patch<=matching:seeds.update(patch)
                        queue=list(seeds);found=set(seeds)
                        for x,y in queue:
                            for p in((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                                if p in matching and p not in found:found.add(p);queue.append(p)
                        outside.update(found);bounded_floor.extend(sorted(found))
        if gbmap=='GUIDE_GENTS_HOUSE'and origin==(0,6):
            colors=set(self.gb_image(source_floor).get_flattened_data());pink=(255,156,197,255)
            assert pink in colors
            seeds={(x,y)for y in range(16,height)for x in range(width)if whole.getpixel((x,y))==pink};found=set(seeds);queue=list(seeds)
            for x,y in queue:
                for p in((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if 0<=p[0]<width and 16<=p[1]<height and p not in found and whole.getpixel(p)in colors:found.add(p);queue.append(p)
            outside.update(found);pink_seeds=sorted(found)
        retained=0
        for gy,row in enumerate(layout):
            for gx,mid in enumerate(row):
                mask=[coordinates[gy*16+y][gx*16+x]is not None and(gx*16+x,gy*16+y)not in outside for y in range(16)for x in range(16)];parts=[]
                for zx,zy,zw,zh in source_cutout_zones:
                    for yy in range(max(0,zy-gy*16),min(16,zy+zh-gy*16)):
                        for xx in range(max(0,zx-gx*16),min(16,zx+zw-gx*16)):mask[yy*16+xx]=False
                overlays=[]
                for part in additional_parts:
                    left,top=max(gx*16,part['x']),max(gy*16,part['y']);right,bottom=min(gx*16+16,part['x']+part['w']),min(gy*16+16,part['y']+part['h'])
                    if right<=left or bottom<=top:continue
                    overlays.append(dict(donor=part['donor'],srcX=part.get('srcX',0)+left-part['x'],srcY=part.get('srcY',0)+top-part['y'],w=right-left,h=bottom-top,x=left-gx*16,y=top-gy*16))
                if overlays:
                    # All native GB overlay pixels are opaque. Omitting the
                    # fully covered source fragments leaves identical output
                    # while keeping the reviewed32-part atlas program limit.
                    for part in overlays:
                        for yy in range(part['y'],part['y']+part['h']):
                            for xx in range(part['x'],part['x']+part['w']):mask[yy*16+xx]=False
                for span in runs(mask):
                    # A span may cross an intentionally repeated8px book row.
                    for yy in range(span['y'],span['y']+span['h']):
                        xx=span['x'];end=xx+span['w']
                        while xx<end:
                            stop=xx+1
                            while stop<end and coordinates[gy*16+yy][gx*16+stop]==(coordinates[gy*16+yy][gx*16+stop-1][0]+1,coordinates[gy*16+yy][gx*16+stop-1][1]):stop+=1
                            sx,sy=coordinates[gy*16+yy][gx*16+xx]
                            parts+=self.gb_rect('crystal',gbmap,sx,sy,stop-xx,1,xx,yy);xx=stop
                # Merge vertically adjacent source/destination runs while
                # retaining exact native coordinates and complete glyphs.
                merged=[]
                for part in parts:
                    prev=next((p for p in reversed(merged)if p['donor']==part['donor']and p['srcX']==part['srcX']and p['x']==part['x']and p['w']==part['w']and p['srcY']+p['h']==part['srcY']and p['y']+p['h']==part['y']),None)
                    if prev:prev['h']+=part['h']
                    else:merged.append(part)
                if donor_palettes:
                    for part in merged:part['donor']['palettes']=copy.deepcopy(donor_palettes)
                if overlays:
                    merged+=copy.deepcopy(overlays)
                    for part in overlays:
                        for yy in range(part['y'],part['y']+part['h']):
                            for xx in range(part['x'],part['x']+part['w']):mask[yy*16+xx]=True
                assert len(merged)<=32,(label,mid,len(merged));retained+=sum(mask)
                base=target_floor[gy]if isinstance(target_floor,list)else target_floor
                if background_bands:
                    background=[]
                    for start,end,ref in background_bands:
                        a,b=max(start,gy*16),min(end,(gy+1)*16)
                        if a>=b:continue
                        py=a
                        while py<b:
                            h=min(b-py,16-py%16);background.append(dict(donor=ref,srcX=0,srcY=py%16,w=16,h=h,x=0,y=py-gy*16));py+=h
                    base=None;merged=background+merged
                role='reverse_gen2_hoenn_'+label.replace(' ','_')
                art=self.composite(base,merged,role)if merged else self.native(base,role)
                art['_objectMask']=''.join('1'if value else'0'for value in mask)
                evidence='Complete '+label+' from actual Crystal '+gbmap+' at native1:1 pixels. Whole-object exterior mask retains every enclosed highlight and exposes the actual selected room floor; no frame, feet or seat is cropped. '+('Original native rows/columns remain intact. Empty source-canvas margins remain matching wall/floor and only explicitly listed plain bands may repeat; the visible foot anchor is retained.'if row_pixels or column_pixels else'The complete object has the same source and donor footprint.')+' Original foreground availability is retained; its overhead silhouette follows the complete classic object rather than painting room-floor pixels over actors.'
                if only_game:self.add(only_game,pair,mid,self.prepare_art(only_game,pair,mid,art),evidence+' Complete source family was independently fingerprinted and context-reviewed for this cartridge; no RSE alias is inferred.')
                else:self.aliases(pair,mid,art,evidence)
        self.contracts.append(dict(pair=pair,source_ids=layout,gbmap=gbmap,origin=list(origin),dimensions=[width,height],source_rows=ys,source_columns=xs,retained_pixels=retained,pixel_scale=1,label=label,preserved_native_rectangles=preserve_rects,source_visible_feature_bounds=source_bounds,source_and_replacement_foot_anchor=foot_anchor,background_bands=background_bands,pixel_overrides=pixel_overrides,bounded_original_neutral_floor_zones=zones,bounded_original_neutral_floor_pixels=bounded_floor,plant_interior_floor_pixels=pink_seeds,native_palette_variant=donor_palettes,additional_whole_motifs=additional_parts,replaced_nonstructural_source_regions=source_cutout_zones,explicit_complete_native_seat_contour=explicit_contour))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--contacts',action='store_true');p.add_argument('--pair',default='building__generic_building');p.add_argument('--game',default='emerald');p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');p.add_argument('--previews',action='store_true');a=p.parse_args();assert not a.activate or a.validate
    f=Review();f.inventory()
    if a.contacts:f.contacts(a.pair,a.game)
    f.build()
    if f.rows:
        f.write(f.out/'candidates.lua')
        if a.validate:print(json.dumps(f.validate(),indent=2))
        if a.activate:f.write(TARGET)
    if a.previews:f.previews()
    (f.out/'held.json').write_bytes((json.dumps(f.held,indent=2)+'\n').encode())
    (f.out/'contracts.json').write_bytes((json.dumps(f.contracts,indent=2)+'\n').encode())
    (f.out/'preserved-black.json').write_bytes((json.dumps(getattr(f,'preserved',[]),indent=2)+'\n').encode())
    (f.out/'intentional-exclusions.json').write_bytes((json.dumps(f.intentional_exclusions,indent=2)+'\n').encode())
    (f.out/'dynamic-source-inventory.json').write_bytes((json.dumps(f.dynamic_sources,indent=2)+'\n').encode())
    (f.out/'secret-base-decoration-inventory.json').write_bytes((json.dumps(f.decorations,indent=2)+'\n').encode())

if __name__=='__main__':main()
