"""Source-guarded Crystal counterparts for every FireRed/LeafGreen tile pair.

Only this new Gen2-theme module is authored. Ambiguous motifs, changed whole
object footprints and unmatched silhouettes are recorded for final review.
"""
import argparse
import copy
import json
import re
import struct
import zlib
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import catalog,preview
from building_review import decode_layout
from reverse_common import ReverseReview,ROOT
from reverse_kanto_review import aliases,donor_map,native_animations,exterior,clip_parts,ground_ref

TARGET=ROOT/'mappings/reverse_gen2_kanto_finish.lua'
GAMES=('firered','leafgreen')
UNSAFE=('reviewed_brick_house','reviewed_closed_','reviewed_celadon_','reviewed_silph_','reviewed_soul_house',
        'skylight','fall-warp','entry_rug','counter_right_flower','architecture_','kanto_whole_','parapet_or_floor','invisible','original_fall','original_open_void','original_unlit','wall_handlebars','original_movement')

# Whole16px native water surfaces visually reviewed in water-grid-01..05;
# bank corners, waterfalls, piers, bridge posts and beach strips are excluded.
PURE_WATER_HASHES=('2542322850c091953958aba58ad7ab512c1621f4f969bc4cd2ecf2a9778bf985', 'f1c2fb48967124a3728bc1706a83ac082ad19ea73e319d6f17b0540d101667c7', '037c2cb2c4abb18bbba3e60a79453cae96784fed6e76f85190ae331182488844', 'b58c94afcfe6de5fb80f21dbc59be2a23617b9fb5690f63d289be86fc0269371', 'f0d36da967de25e04106e0e44971a4c1a2d69ec66c7ac4cddf53f7be92262a8c', '859fb2917a056aa87cbd8fbb49de28e14f148852bdaec1f4dba30dd9bc84b263', '17b04d17214b3b1db68b1bad68679b1569fd4516f3c7766afb6e734524cfedc6', '579c28ec7ee04e372e0a9561c8362063eb4b76afdaf4147c5c85716bbbaf6f85', '6bca35a47fc48665a2df259eb3d37b38410ca8354074eb00013748d4f33dc8d9', '7997bf7918238b65b0cfd2de5daf0ee075bd5739817d04d2fffc4cb9a94c78eb', '3d7a26a8ab425266a396e2d032b67119067271ecc6c00f360ab0357cce969603', '6749fff28b1d7096ede9197631e0a1b074853cdbae9b13cb3137fad1c22a6b6a', '166c4e8eb9c6857c7426272e491b2f2fb802d5a396d41bb7a7c1ce4067e66003', 'a210c8b0dfa1458c509adb3fc0155e939640e97b7d84828759c03882dde56b2b', '4c427d1b34995fcd311e4b002beed7d66b65b4de3baac12bb7b2528b06344c8b', '45decebb050f6656f8134583c3423ad7ec3221a7adcfed846a95920fa5883d60', '6461e9cd2e8d2485e025aef23f68cad5f31ce3deb796163f0e77e70b646f0449', 'e840f242bd1779e6993979a1222e852b7ae526f73f52246d2aca02cba14c6235', 'ddabd6d5810ce689fd9f7f2c6ed7c8fe7cda6ac83f30a18be11d376adef17f5a', 'c06a0c0e5c3741f583cabab85570227a31a6b7e60082d8346abff8ac32316f3a', '6f5dca9eebe6786bccf34260c90fab69506bd8fc041a67d4fbfbc0d7739c1fa0', 'eee4399599170f5aacf45c255001ae7ad9f680555fe828b7a0ac24788a473825', '600aee0b9dd676be60ecbdb7121b22d89fbf3139e96c7b59f0a65e8e4380ad40', '3c0823b437a01c70f1db8979c6dc7b4df86e615d25b59563cec8c6683274b0ec', 'e2be8b215ef56e3a2161e1f7b912cf8ff99b846525d33bc1ecea7edf4fc4573f', '0c29089f8758d2177398d1f81a81f4a452759680a0f3673811ba198c3e689f35', '15aa5b5e7b707609485b6d94fb757256ed1ec4633cd47085491c6335ab37b42d')

# Explicit source-resolution material review (cave-grid-01 / other-grid-01).
MATERIALS={'aa3d0f944be08cf0dfbc6b88467acd99b803b4121c9c3bc1ee2672f5904a2711': ('MOUNT_MOON', 5, 0, 'solid_cave_raised_rock_fill'), 'b321d6e42d89b4de925ba49cc14236964361ef7d870a0273745b5ed06020fc05': ('MOUNT_MOON', 5, 0, 'solid_cave_raised_rock_fill'), '4583d406fc06ef3508f36c6a4182ab25c705af271a1aabb4e6a46527912ef957': ('MOUNT_MOON', 36, 3, 'complete_ordinary_cave_floor'), '258f6c4b61a4cb2be9445865d114a31439beda37c0b99662a51b0240f70aef75': ('MOUNT_MOON', 36, 3, 'complete_ordinary_cave_floor'), 'd3f2210bd11aae63814ea1d04f85c815df9e04b5a36ca900d428f11155173681': ('MOUNT_MOON', 36, 3, 'complete_ordinary_cave_floor'), 'ce211da1cff6233932e8d77805dfb82114841b84c359e4428556e7508bbf5616': ('RUINS_OF_ALPH_AERODACTYL_CHAMBER', 5, 3, 'complete_ruins_stone_floor'), '069d1525a58bb15aa1f4bf85a056ca912c5a37c8079176e9d8876fcc4b182046': ('RUINS_OF_ALPH_AERODACTYL_CHAMBER', 5, 3, 'complete_ruins_stone_floor'), 'deb5f721b4b81d6fa3dd8e93b60349bf3936fefe07ae2c87f2658b5f4c8ad773': ('RUINS_OF_ALPH_AERODACTYL_CHAMBER', 5, 3, 'complete_ruins_stone_floor'), 'cb05b2a22353a74ddf2e1d7b277ea6fbb45b2fa9f6f371fc594bedc6bb299d30': ('RUINS_OF_ALPH_AERODACTYL_CHAMBER', 5, 3, 'complete_ruins_stone_floor'), 'aeaf2d453bc64ae14ce341d5bcc25d811537e97f2a694ad972762bbe60595e8e': ('RUINS_OF_ALPH_AERODACTYL_CHAMBER', 5, 3, 'complete_ruins_stone_floor'), '19e194c11e7883838c681c8c164700ad230de2c43aa89cf6a73b8689654e5073': ('RUINS_OF_ALPH_AERODACTYL_CHAMBER', 5, 3, 'complete_ruins_stone_floor'), 'b338fb7ced084d512a5f0b384dc91697e7c20886170e421631ba90bf1ca2fa9b': ('RUINS_OF_ALPH_AERODACTYL_CHAMBER', 5, 3, 'complete_ruins_stone_floor'), '39f690ef505f74f8d9da2d81fcc2bf82d2ae6c818739a44326bcf7748a2de296': ('MOUNT_MOON', 4, 3, 'complete_raised_plateau_top'), '28d3db14215ee680455cac3035d6b4aad2a5505fb4f38bb6e428eed4c79618b2': ('ICE_PATH_1F', 4, 3, 'complete_ice_path_floor'), 'cf6a827013959c6f5424e5b19957e3eaa420df4434badee02cf79e1465a2b988': ('PALLET_TOWN', 1, 0, 'ordinary_nonencounter_lawn'), '8bd55aac8b2a16c9a84ff68c095b48f44e6b1074d448da175d461f5d852b0d40': ('CIANWOOD_CITY', 1, 0, 'ordinary_sandy_open_path'), '60ba133d7380699bbf480495f677e94c0a5ead156f374a3eb6a68e7e699f1d5c': ('CIANWOOD_CITY', 1, 0, 'ordinary_sandy_open_path'), '31f452eee54503e75b4cc600959d064d5877342933903c1b10341f249d62981f': ('PLAYERS_HOUSE_1F', 3, 0, 'complete_horizontal_wood_floor'), '49baa7f132114b160f2abfb2bd71abeb420e2ce188b6afac0657f3d6781eca4f': ('AZALEA_TOWN', 113, 0, 'complete_raised_rock_top')}
WATER_ROCKS={'cebec3f442c6a5ed0e48b5ba8aac6c74c54c348ad2bfc68827455fe29c924333': 0, 'cba14c2912928764ba32f4cd5f2206cf5bce3912d760658f4224bc3ce7f7d0df': 1, '33996086cac991dbc321fa658192c6a0e5a95adabfc2f359cc7e770537c6aee2': 2, '46cea6af2f4bb82fe2abb87190f911bda5114376a7da76effd70298da4b3bf49': 3, '69dd1860ad5cd0c2177fe6c7576c5c8a3b973dd1ad0992d386f1a87924e9b345': 0, 'c1926156a47e92c4384531436934b5f6c66ad69000dcaf4f6e8585adc2624215': 1, 'b2e13b767b2453d2be9ce9f0b94ddfb8d24e98dcb1a20729a2b0c78ed038fe5a': 2, '1410d38ee62d64685fddd9498aef94b15753f4a91f23facb0d83a0b94b0b4761': 3, 'c74dadea6c3c49256ae9bef1c62d95dca68f34b50c5768819367a73e9398cc96': 0, '80189cabed8f85104395908c114b1b2dda8de941fb187cca12ce9f1fd2d0ca1f': 1, '99bf8c85aa479808577d2ab173d18d8ff93625d258e117e9b863b2cfcca3b4bc': 2, 'eb055c355d8e4f0d4f2f4c29df5c5a031c334e76d62f1d8b082f7b830c5524f7': 3, 'ca8d5ad2506b3f5fad6c1f5ad7316f16f729bc6ae696deb72e43b778d8fa47ca': 0, '4fb45a9105901abe50a619803372d6f574f6be51bd02065380edf645013f02ad': 1, 'a50e36ef29cb9561557b37875657a77c848d8bd91b953f1493287ac4c7f76b8f': 2, '65700792afee8f123b3db64c533e44dd1a87dba45ec90ae6233918f0d971b51b': 3}
CLIFF_MODULES={104: ('ROUTE_27', 106, 0, ('mappings/gen2_kanto_shores_finish.lua', 1530)), 105: ('ROUTE_27', 107, 0, ('mappings/gen2_kanto_shores_finish.lua', 1538)), 106: ('ROUTE_27', 107, 1, ('mappings/gen2_kanto_shores_finish.lua', 1539)), 112: ('ROUTE_27', 108, 0, ('mappings/gen2_kanto_shores_finish.lua', 1542)), 113: ('ROUTE_27', 109, 0, ('mappings/gen2_kanto_shores_finish.lua', 1573)), 114: ('ROUTE_27', 109, 1, ('mappings/gen2_kanto_shores_finish.lua', 1574)), 120: ('ROUTE_27', 108, 2, ('mappings/gen2_kanto_shores_finish.lua', 1544)), 121: ('ROUTE_27', 109, 2, ('mappings/gen2_kanto_shores_finish.lua', 1575)), 122: ('ROUTE_27', 109, 3, ('mappings/gen2_kanto_shores_finish.lua', 1576)), 123: ('ROUTE_26', 111, 3, ('mappings/gen2_kanto_shores_finish.lua', 1376)), 125: ('ROUTE_27', 110, 2, ('mappings/gen2_kanto_shores_finish.lua', 1552))}
MANUAL_SOURCES={('viridian_outdoor', 680): 'db0c31065f74078ad9f4db80c2c544b4b29df3a50207ef44adc757b4bd347d8b', ('viridian_outdoor', 681): '80273d8a51c5c29eb75dd68e024a285e9fd9892c5893855433f018301343de5f', ('viridian_outdoor', 682): '80273d8a51c5c29eb75dd68e024a285e9fd9892c5893855433f018301343de5f', ('viridian_outdoor', 683): '54cdb9d06a600412d4110730096a3867324208b64138b876e15ad7af170aecff', ('viridian_outdoor', 684): '8c1895a004bdacea90559c5f0eac38212d2a5d28ba5ee92a3c1c0ce4e11263f4', ('viridian_outdoor', 648): '79a0b992fdb9811525683ec16cc3f15bca11b7a8e4ca792a9e689ec45a33221c', ('viridian_outdoor', 649): '465fa58aeabef6952a4fb6a1115e7eeaaaea79ad8fbf108a2626d1e69404f19d', ('viridian_outdoor', 650): '41c332f4b4263d89205ed0720449a5b0bf130167c65c40e486cb5d023ad14bbf', ('viridian_outdoor', 651): 'ce45db14aab4925bd72761a11d50aeca354dd908c0c428960fefab0bf5f04438', ('viridian_outdoor', 652): '5c3e9965808ee82e618e7a51d8524e4544edf968e7e3f7ae4382e65e4ee1f3b3', ('viridian_outdoor', 656): '203df8adcf65ec979f83b1197cb6d209858e356cbec007537d1b94cd54aeab6e', ('viridian_outdoor', 657): '4c3efc27ecf70c1871eda7bfed69176cf22a9444d22240d0ead19702d3224859', ('viridian_outdoor', 658): '220ee19fe0b034f8fed5745f90755c1eb928a3a8326147196047c4174b141447', ('viridian_outdoor', 659): '852165d60b18364c607d028614800903c7c8fdf322e3c2bb2faba93846a9863e', ('viridian_outdoor', 660): '8fec8946a3f1f3bfa497f366ad213eace539779d2a00dbc4b7beaf73fa357112', ('viridian_outdoor', 669): '93f74bd3fb0dab1acdcf82ad6b07c5552185501a3e0ee802eef78163a6284a1d', ('viridian_outdoor', 665): '208211ce866db10c045f8f5703132a062c3d6823c1f1da5679ed07845a1a4ff4', ('viridian_outdoor', 677): '6c920d546c144fe519491517d842196da7e88256633108897940ad65841716f5', ('viridian_outdoor', 678): '8468453fa0e7d4b099c70fb4ec709b5b6b2d2eb807473b1eeeb3ae12c8b641dd', ('viridian_outdoor', 679): '4bc24adea8c40abb596bf195ca016105dc24ff6576f44182bf02fdc80c3e0a3e', ('viridian_outdoor', 40): 'e391f7f1bf9f53cb477330dcc977e621222898ccc77c22479d07ac150311e7de', ('viridian_outdoor', 41): '22cc799640ac26a23172692cdca7c429060fdfc0ba4f43ac3b93ca958be6157c', ('viridian_outdoor', 42): '53ee8512c7edb5657fb991c6a16dc6bb22be55e3dc03cb2f54af09ef1fe76b4c', ('viridian_outdoor', 43): '7a358c0c6c00a9afec510c1a9f04cb2b4e715ced4eb5f1521e3545e52977f036', ('viridian_outdoor', 48): '4b1f40c86475bd03655a85d5c06e77be17315948d165c59c9fd271a8503f2932', ('viridian_outdoor', 49): '935ea9e6006d062fb281daf348c6feae37bcfa9151a4af42706d88f865a803d5', ('viridian_outdoor', 50): 'ece122eef6d0a8cbb997f0e924f4634da7443fa71dd50c5d01b6c1db8e25ea01', ('viridian_outdoor', 51): 'e42eb70c2458cb9c60e2847cdc5837f7b19f5dcbcf5e42d009fcd3da10c68fbd', ('viridian_outdoor', 56): '03b1947e3d4d5f25ccd6652d93d5057962e0dd1b90464ace666f0632b0d5354a', ('viridian_outdoor', 57): '8e7dad0a5ec16066bb76be6baf2cf4a6ee30a669779189e9215c250a45697a08', ('viridian_outdoor', 58): '1b884c4782ed6531cdb1d125f4e01110e2a490e886669e3ad568ef43707076c7', ('viridian_outdoor', 59): 'eef0aeb990791f9f06e133d3be6c91d3031efda75043893943c810fac57c3fe6', ('viridian_outdoor', 64): 'a976c9358b00243bf8204be4af4e6d5309d46e3ceae9fe11cbe5c8741d1d7d46', ('viridian_outdoor', 65): '7528e0f5bd8ac3ebda3a464eacb906f23b74664e336f770c13b03b2493fda526', ('viridian_outdoor', 98): 'e51ba1552f4025e51f32af68e08c9e90d0f8a51826589c2008469bf4d160aab3', ('viridian_outdoor', 99): 'a7059c8911bbeb48d636adc656efa5e464cdd1338835b5edaa5da5cee90ef2b5', ('viridian_outdoor', 688): 'a866f2faa3dfa1ed5b3d3c3175c5ccd291c70ff0b6359cd6d1916428c3c28d83', ('viridian_outdoor', 689): '439df01e8a0e9f3cbf1e07c7aef0051041ced01afa23429bd34d251002c6bce9', ('viridian_outdoor', 690): '0073fbaacbc8225d56708dbef436798d2b42ebc7e721e75305e9adc61ed904aa', ('viridian_outdoor', 691): '60241a136904290c39264e00e157ff18a8ba1ab4bcedaf3b3ae6bf08b9a10723', ('viridian_outdoor', 692): '22227ba67412a0870766bf146d9a6471c8d4b828440eb4b1586c7187b49aaff9', ('viridian_outdoor', 72): '2fe0152b4c82adb513af5d5a41ef40688b6f9fb0cb859406c184469d739a5c1a', ('viridian_outdoor', 73): '509ca594dedaa52cb819100ec117f0443c89f591fbb36b14d6dc6f55ce3865bd', ('viridian_outdoor', 74): '32f72b924d2677bc1974bdacd146bd8ca9de106d0c51cbe523eb8f6803840cd5', ('viridian_outdoor', 75): '0dc2fa0e7e5ce5c92249cd0f9016c75369e5f12f2bc1c325a7d7b3a43f292654', ('viridian_outdoor', 391): '067dbd480b35dc15208efd568a5f50b7d1dceb97aff8e18fee8b51ab19000a63', ('viridian_outdoor', 80): 'da781cdb49aebd3a83f7ff54a4ac4db86ce0e128aaac9eb8684d9614c5169820', ('viridian_outdoor', 81): '0050b8655dfe21654e5f3e59bedfac4b245b0e5f195bcc7feb3eb911ae12f958', ('viridian_outdoor', 82): '50589f0d0680d9c98e8785b3b2c2e65b7bc7970b79961fe1413a06225be30124', ('viridian_outdoor', 83): '3488982f09414d91fe1888fea3ce64d85aa7745b245311cceeb980521d80d84a', ('viridian_outdoor', 399): '11a5ea09aafd87b1367930b920775b70d11a214bdb5bd7ea107b193b03a4e914', ('viridian_outdoor', 88): '4cd4b20fa40026bbc32c0dcb088e1c78585ce862d447804f7e41fbb709018c56', ('viridian_outdoor', 89): '1170e9cdde783f5b5e35a2be627f4f1f0beb6cd8fa320b039403c34833f4e734', ('viridian_outdoor', 90): '91c7f480f2a3e1ceba76870a6d6f07e22d93ed124e1f328cc0b44fd61a346574', ('viridian_outdoor', 91): '48243adaa717472f7c7a4ec90461e7800c74dbeb60c8bde8a5b8916e07e2cd47', ('viridian_outdoor', 407): '2b5fdc4822778e946e6d5d025c09997a58b6713a06daffa2a3b0c2143df5ea0c', ('viridian_outdoor', 96): 'b49f353e62f598e78fa178ea6a24d36b207c36172a39fe2e371caa4a645d3a06', ('viridian_outdoor', 97): 'a2b07e6c8e86d7af087b22a44fdabd26e467c1c981b9508710b1bcbbc09f1277', ('viridian_outdoor', 390): '9e752f2fe6fabf75862057b2f86e067d65270b7626a5780fd4441d534530d8d1', ('viridian_outdoor', 415): 'bd0a8aed7ee05f88174325eefcc51c0911342244d2e1af88b39b91f737db6551', ('oak_lab', 107): 'f0c164d155d6b977ea63fe75319516cbbc872f9aa53fa70cc3339424a8bb694c', ('oak_lab', 108): 'b979abaf4a39b9f9e1edb3a585a77528c536700ac1365b6acf0242b82993a0ed', ('oak_lab', 115): 'f9c9ca02e3aafaaf024ee32bdb16679b804f2e59ac5fa3ee57be1b8308bc893f', ('oak_lab', 116): '12c211efbd241018798c8c6348ad42247f2842d439c8d32086e8cb3bfa6821f4', ('oak_lab', 643): 'f53f13d7f96b568b759d521f74896d17ab72a753adf4345380f11de946af26e0', ('oak_lab', 644): 'ccf3c15d63423ccaf97d81e47eb86e5a4486441bc261342f9d643b1c3f07e281', ('oak_lab', 680): '798685045b10641e7174dafeb23253fac04d60a17c09d246ead3bcfe84491206', ('oak_lab', 681): '4b3aee9f205a4f85fffdd14b32828859a7feab37a2180b41cf9cdb9d3efcf769', ('oak_lab', 682): 'd64769549bc7788e3ef9145ef14019a27990b098b1ee8b15de2544d9666d0557', ('oak_lab', 688): 'aa23cc10a573368086ecf9264adf38ac729eac37d29f668a3fe22fb77114e7a0', ('oak_lab', 689): '3f7e3e490acae8b05d7cdfab3bb160c3f16cecb7e83e9dd38f74d6f30e1b578a', ('oak_lab', 690): '8ccf83246d1f7e815f91ca56416648461de0a4be0eb2c2cf09e1211199e9b405', ('oak_lab', 649): 'a72264f02099daaace319ac2b340e67399481869a3b06fef553b9f83cba13995', ('oak_lab', 105): '4f62be1cc9d88d68e65a77720c831666c5ff81b6b491027ed6a8205d499b8eba', ('network', 697): '01e22bb5793da097ed913fba55202d9155f389e5f35cfd5510d475773f01dbb8', ('network', 700): '137294e6ee7e8c8ba0bbe9293bd7635e4967fd0d71be606a5b0b20dff6e6baff', ('network', 664): '34f7b942e04bdd9966d339e0c6cb681334c48a91dd48ce8548cc1b0564bc8b39', ('network', 701): '35a82cdb449f00d5333ef117aab68ed65b0a35b96767f513f61ad4ea70b32ee0', ('network', 685): 'e573f37d7052efc6ca352c8c6ec4c0896e7d92ac9c663b2c5730348bd354837d', ('network', 693): '782f2f218028a7070a1f91736ccc06fef38ee390fbe726e9173464d1b19994f8', ('player_house', 1): 'ee00ea46cdc8a4093177107e2c7321a10fe34cea70262717b6ee0e74304b56f8', ('player_house', 67): 'a5f236b22419a8a48b8db33eb61adb4bf69c760d7d00c98c89a246e35496e104', ('player_house', 68): '8b7587445ee294cf024fd1ed79de82c8ccf5d85ca72213bf5fe87fcc689a4e49', ('player_house', 70): '65323996c63bdf81ef384b48074c77a49a4e975cdd927d2d3a449824c4d2dc9c', ('player_house', 83): '95aeb4e0cd96ebc4789113b97ce6413bda84aa5e2635aa9ec564380b9f09e58b', ('player_house', 75): 'fb269131bc67b8e03e2e4f79aa00728a889e79d0da3ca8a42dc682ea317eba10', ('player_house', 76): '761b76c0971f669086a4ec8e7b0a548538cadf98ae9bf734f6a4e7ed1d83ec2e', ('player_house', 77): '85d09898ea14eb24f9c4bed1988177a30be07418f0bf8f8ece93cb3e65eea4e6', ('player_house', 78): '07f5f2ccde63dc5bb076753915e0acf347f0ac28f900892b669aa786afb7d530', ('player_house', 86): '2c3d94ae9175044ce02fd9ca90dcf9c8958bd7c5baea32f9dcfbee43d120fb33', ('player_house', 84): '40ff061b1b1dca6154942d96d6a19b2affd8a46859b5a057998a7dda589249a3', ('player_house', 85): '146c8d2a99551cc7aaf9fef271a25cfa300828841a27139da442346c0d97a169', ('player_house', 91): 'c24be63fd495bb3b6562d6cad456829135db2faa324bdae08aaabb40a560ed29', ('player_house', 92): '2643da55d56aff37747724dc8b3f5e229e45d238d4f50487b2a96f9a6fd6340c', ('player_house', 94): '4f5755d384232017dcd684a35082ff94e9e096670661bee90bfba20e6ae46983', ('viridian_outdoor', 357): '951bf2106d2872987044ce4515bd59128cf2b7a30ea0e177564c4eb869ddc902', ('viridian_outdoor', 358): '1c531fe79488dd8205114f7be83ea01becb23eb6a8f9ae01579a2fd0521b2493', ('viridian_outdoor', 359): 'a684594dd2c7969d783ada97895de8bc1c91dbc7f5118a7bb40bcae3251e2b47', ('viridian_outdoor', 365): '60976132469a02c8d8bf1e06cb8e2fa62b666fabbd33fe6c1ed4a1fa3d53e098', ('viridian_outdoor', 366): '52d2eaecb8f3d0291ac10c515ccac92fd548828b14a96045666e52526b7c725c', ('viridian_outdoor', 367): '18071495707bfe8594a3335fd29afe6861f1c34a82733f7becd12dff8b76eaca', ('viridian_outdoor', 373): 'f015de7847484c0efb2edad99160baa0adf4bebd7571fdf3ea8f42afa234baa6', ('viridian_outdoor', 374): '30291c3f350961486ad31210b5ee0d478eb81b35d8ffe729bb743db3fa3b7a61', ('viridian_outdoor', 375): '6f4a74de47154ebdd68e3bbed932afb30ccadaa5cef46d42a2db2387f188ad9c', ('viridian_outdoor', 405): '9f0a2c7b1f44ac879b955cea8af2bdd0d37366a9c1e72a76afcfbcd2d467e2dd', ('viridian_outdoor', 406): 'c1966be686c1a18e8864aaf959c401b626f160b66690db9b1a59dc2371e730fb', ('viridian_outdoor', 413): 'f1554974606866233f382de18a33b109639a728727e9003dd7a75b9fbc45d0db', ('viridian_outdoor', 414): '2d2833fe95e016859e91493b561d00716cac2d0ebb58b9a1ed6e2ce7306c542a', ('viridian_outdoor', 212): '64616ade3dee224740307b15e776859eb4392d3b95ae37e52adb8dc8e3eb29fd', ('viridian_outdoor', 219): '87d729ede90bbf28b5d1fbebe29c252237bc593baf85ca74e14941f174b139b4', ('viridian_outdoor', 221): '33e766e5fdb9e4c7865005aba45b01fa7fd13552defb95b5150482aa4e478c70', ('viridian_outdoor', 228): '1ddcfabe336287a6a11b33a19f4b8ed7a141fd19d08e1772cef03ee029db85ac', ('viridian_outdoor', 230): '2adf278e90646e5e921aa60eddabda0dc1166f11893888b804b7c7adcdad9c3e', ('viridian_outdoor', 231): '4b9059f2754123de41b1aa6d8ea171aa131e395712a39a1db9ed8b60ee7d902f', ('viridian_outdoor', 321): '16c26439df9d03d7d960011d7883dcfcb672aa11039b3273cf4da7906a7bcb77', ('viridian_outdoor', 322): 'a83a6907f50221daf3b5bd64fd032e41522c703b6c0c33f8658ade044f30899b', ('viridian_outdoor', 323): '4f50648f18bc2c8e8b881c460d690a423f162359e615a271c080534b7c4d7944', ('viridian_outdoor', 329): '548d7f1e15d2526ed5d64cb5479283e40d9f559518e10bf114db6f9f12a9f30e', ('viridian_outdoor', 330): '3246d7d6c604ca90d4328e74336af9c618b02899cd8aab7778df36cc2dbde46e', ('viridian_outdoor', 331): '01558dce8a6b0e54b9dfb5656cd00a6c4eb5d2111391f21d946c5078e0c0b3c2', ('viridian_outdoor', 336): 'f49b9222d7e7e54df75781a62e5c359f001688be6991e1041c6e60000d79281f', ('viridian_outdoor', 337): '0f9388f3005e0486c0b89b3ed97ff92e7c8ad8dee58e20189ddb23e5a0ef4f52', ('viridian_outdoor', 338): '70f3b8f886de4f53a6bcf442e30c5daaaeb19c7dc384f3c289685ef6573f56a1', ('viridian_outdoor', 339): '43b3e5d17ddfb4170ec64b7cc52225631429dbc4549433cffa2a9e3994046006', ('viridian_outdoor', 340): 'fd0d2bfb0d461afa85514052b92dcca58a836dde8722bb3a2be32928c03e73e8', ('viridian_outdoor', 342): '338c0e46f5272f05e7c6298ea7cb7f1756f552573ab8be51d7c270b7bf852860', ('viridian_outdoor', 344): '0ca83a2b7361b61c756a350b82b4591f560a3c9176ee6ec7c47839dd4c2558ac', ('viridian_outdoor', 345): '3089125f07d4b2b7932c1146fe9cf19ac9eabebc228092575698bee8f1cfc0a9', ('viridian_outdoor', 346): '5a9c6a09b3043c00852714fe3ed1b36d8be72dcec390f229711ff05c1ef69806', ('viridian_outdoor', 347): '7b5e8a4e98915ecf231ea8f1bdc6be5683f55f2db6dae8ed01fab780dc28dbe6', ('viridian_outdoor', 348): '267b41cefcdee622f8a30eaf68665bafb9bc2732ddf7b9019f08580617f9b5b9', ('viridian_outdoor', 350): 'f961f9c46d22cbd372920352c7b600257c38ff2d208789b1ecabfb46afb5919c'}
MANUAL_SOURCES.update({('general__rom_082d4bfc', 641): '7c00b111759c0a0f43147fb3ff3c4965087813bf076f7de5d3787de05c2d8ea4', ('general__rom_082d4bfc', 648): 'a530ae707e3a661089709786bab783a5aa772e9549f5b18eacb2271b9eed8e85', ('general__rom_082d4bfc', 649): 'f27c6ef5201650d485fe4bea1713335613560622c88e12d9cfbe078bdc34362b', ('general__rom_082d4bfc', 650): '33f9738388b4d2b9d1aedf5ce81d1bee98be87a308fbc6557b280a4b88c5c0ee', ('general__rom_082d4bfc', 656): '03f761690b9e273099f5878290ebb82836361801feb6c51b01d6d81ff9b88018', ('general__rom_082d4bfc', 657): '84aa5718b8441016308f1fc3d738b9a79e325484a752c80ac1ddf04755360e5e', ('general__rom_082d4bfc', 658): '10617f3b651258211e9c9eab35683d56ec190104efeec96e46dac81d5940609f', ('general__rom_082d4bfc', 664): '0b52679ed06f96d7d893360b51253b182ceb0f98b349d828c8d0fd5ea8959bf9', ('general__rom_082d4bfc', 665): '4ddf9fef06746d6adcb7a3398f35062527e4f5d3f150152b33b97b8e3e593e35', ('general__rom_082d4bfc', 666): '5655ec4829c3219cf398f264765a38ac38c3e629fbc45754e8dd4469cfb127e1', ('general__rom_082d4bfc', 667): 'd24cdf9e811a2b0b1ac071679cc3f19f6fa3ff2a919108370fdd681969f45619', ('general__rom_082d4bfc', 668): 'e4fef1625119b6a3f390d5ada5ad70b15ef0cae28d24e26c0c7662d7fd8e2853', ('general__rom_082d4df4', 641): '5fc0ed6df9e6909c4fb41951ffdc21fab382561e183b2482311260a1d186de35', ('general__rom_082d4df4', 648): '3956a7d76608179bff0892995f562da13521d6999b6e57d6e2124a2d811135d7', ('general__rom_082d4df4', 649): 'cd2cdecc3c74a9789e96f4e555691ae9331afe019ed1e1c45473768a49973f8e', ('general__rom_082d4df4', 650): 'bd5e3112678304c2b3d17afaafab104589dc6362ad94763cf174780a0924baba', ('general__rom_082d4df4', 656): '881745e77c53038a116d679e293423df9563972deeace66f05d23beb8dda1580', ('general__rom_082d4df4', 657): '088149cc561639b71b34181fe2fd14b3cc00ea41860d7755975b7695c0bf3bc0', ('general__rom_082d4df4', 658): '8faec2167b26801890ef58bf1d252de4ae1b9a9ea1adecb8f8aa972ec6d92841', ('general__rom_082d4df4', 664): '916fbb6d48689fb28558fd2bdd957624ba5cae1fc81537c6a88567af6211dc6a', ('general__rom_082d4df4', 665): 'e4eebbed04732fcbee7ef303db4648c09e1617a3241acf4f67a1a79f5c910512', ('general__rom_082d4df4', 666): 'a9e3cd596f5af11a4f35e3ce9b503329dd3dcd38804924f1fe6885adcc25fcee', ('general__rom_082d4df4', 667): 'dc3f24a4f28fe4b49248698527071dc7c86e4e97e79caa789fad2544b4665979', ('general__rom_082d4df4', 668): 'fcc1e0b960eb98e2598f50c706ce819cadc6a8687e97eba7d71544e12513c786', ('general__rom_082d4e0c', 641): 'fddf002a22f06102111aa5133db25fdae8d3e129eecabafec7eecafe907ec543', ('general__rom_082d4e0c', 649): 'f01e9d4d1b0a093b155d20652cb09c84fc8b4e5fd032967650b7a6c4f450041f', ('general__rom_082d4e0c', 650): '913005b38bbf061daa5d2532410dd347e0480282538190577db58c22ac5fc0bb', ('general__rom_082d4e0c', 656): 'f578ce498ef11c5cdd283880c58aab0cddfa662dbebe63ecff0893a367bd7933', ('general__rom_082d4e0c', 657): '372ff3912e41ee1c2e554b839e3bdd9bb5203dc4e50639b4298101702b85be91', ('general__rom_082d4e0c', 658): 'be08f0a54be61de33665a41fefad1b53a6a7598f64c9ff72c73a5ab74572f730', ('general__rom_082d4e0c', 664): '48b99f65a02e06d17dc9d4570c77604382733b47090cfddc754cfa5ee66b49ed', ('general__rom_082d4e0c', 665): '765b20af278e52b75bc75bc30afa5251727fdf2dc4ce93466013ff709c840a53', ('general__rom_082d4e0c', 667): '746f202fcd8ba1fed0cd2d84a9c4d71ccca57dd98aa0e9103a479dde19db2e8f', ('general__rom_082d4e0c', 668): '6fd44f0eb02c56f9cdded17451157429b0ca6b6943a7d07a7886a5fe1f4a2aed', ('general__rom_082d4e54', 641): 'ae1228caa581a56290f5d4b70b310a2f26a173dd3a1f90a6a95a43abefcb3264', ('general__rom_082d4e54', 648): '6a5e6180555196b460f93f354a6417391a81c4e2c2e0f28cd3bb973e71db4fb8', ('general__rom_082d4e54', 649): '3f8912476e43be4ad84773d7ff60e941c42b371110dd3066615ce3d3f018bef9', ('general__rom_082d4e54', 650): '141fdaf2989b4b4897261c7c9ff64f902faa0fdef33b442686e92fdad36338da', ('general__rom_082d4e54', 656): '62086d5a4123a134df71b10a6c9fc2134c6b28904dd5e20dd9fea5a160f71870', ('general__rom_082d4e54', 657): '3147bf37dc6147bab6b10ad1f70b58ce85f44570577479b4d689590e3c95b316', ('general__rom_082d4e54', 658): 'e14f9da246329d22bb604850a1d5d3413ae4978e6f17ade7a8b294c908cb3195', ('general__rom_082d4e54', 664): '27c0c8e64d8e992d3dfb979d93a82f0e035c21eba8ddd86ba334b7dbfcef1b3f', ('general__rom_082d4e54', 665): '6a39919fd70b586bd343d01217828a7d2927fe9978ee2c6461f6b34aa1d10fee', ('general__rom_082d4e54', 666): 'c2dd8f1635017e175720b108655d65ba26591bbd5ae8b473d5b81024d067a75e', ('general__rom_082d4e54', 667): 'e867ba8960b76c6570218da370aeb3a935ddeec5f95c81bf3b4d7bdae00fadff', ('general__rom_082d4e54', 668): 'a5f5f92e6d6cb341e01099fe88e881b3ae50e03a52d0096a081d5fc2f46bbbfd', ('general__rom_082d4fec', 641): '09f676ca0709d640fc6d16cfbce65f5fc5bbc27fe47f14146f5d7f994d06f58a', ('general__rom_082d4fec', 648): '9c81a6333c325e58ccc73a5c7a9bd85c44340805d7c90f4f15efc8466129d34e', ('general__rom_082d4fec', 649): '45311f709b779b3042c85e5dd810769fde3c086c8e365528d577b80e0df08107', ('general__rom_082d4fec', 650): 'db4786d7be71982a7cc1e5e2ef3eeb01d59105600110048215dd0265df77ae00', ('general__rom_082d4fec', 656): '5f9c3d2bd9a9f614b50097496cc02f959633a671809335b2d734f444d587a0ac', ('general__rom_082d4fec', 657): '9f584d3f2cd153232144062d098960cef6b13269e88214199a9845c75ef9c5f5', ('general__rom_082d4fec', 658): 'f07c495addd335a2d0457453fb0325aa0c1147e4aa394ca2b190661e8d5181ce', ('general__rom_082d4fec', 664): '74b84e79ffb6132bb6cb0108797e18242490d3e138cc52bb313b4b9f9613262b', ('general__rom_082d4fec', 665): '40b386eb9a1bb66eef3d868a8975e1020b5c1675abdc53e9579b34788fd27d79', ('general__rom_082d4fec', 666): 'eb3b939161f8c10911c394514fcf0b70515d442492be4dcf59892d3ab1218a11', ('general__rom_082d4fec', 667): '1a6868188cde2560f329c47ec8cae06eed99696da4c3b7621e873419ed4b7a35', ('general__rom_082d4fec', 668): 'c618ed22e42c7535be04b80b2b33e9807984413a5803ab8aec6fbcd52b481bdd', ('general__rom_082d501c', 641): '2641db391478ef5ddf91c8a54ca6443c638437b14aadd952d61a63c076d8eab1', ('general__rom_082d501c', 648): '448959f06e5b92e2740a9d7972a06b6cd37bf82e29cf579fcc244b5b68634bb1', ('general__rom_082d501c', 649): 'f8660e5c34856ab31222952e8883ff0d0e39d060878ab025b7539035889cae0a', ('general__rom_082d501c', 650): '5bf8c0c614aa3b5c6aa3477355721626c4ff00975cbca0467c76d7e115883aea', ('general__rom_082d501c', 656): 'e9f1a6a2bf4612670c29510c4c6ad365d0ab8e064dc0e80ade78a7805ae81a98', ('general__rom_082d501c', 657): '97441571665b43bd651918fe3438220ca73eca35e44d8f6642b0b961def4e932', ('general__rom_082d501c', 658): '593eda4266d63b39d881c92f61c32a9e63a346cf5158819238cd3180d583d23b', ('general__rom_082d501c', 664): '9e381bd9455a1a468c0783302374aee886c2f98a04e82d65573683a8a769f89a', ('general__rom_082d501c', 665): 'eab6eb288e29c2f237bb0c4dec5aa5a9500bf9d2fec5461c27187470620730c4', ('general__rom_082d501c', 666): 'd137e160dc8a2e12bff281950165ea1308202b3f48c10f307d59598e8a4e66cf', ('general__rom_082d501c', 667): 'ed6c3beebf79b62694d7bf07b2fc3fbbc0ae640bc0c3ccac197467a39c31f0f3', ('general__rom_082d501c', 668): 'c3e2d5a71dfd9c8ac1aed052d38ad4be93e5292c8493c29d72d7c5755b43abf5', ('sevii_outdoor', 849): 'd343cd086e88d1350bb5e85036f9e36ec115b21a68f5312788217574b5d4886e', ('building__rom_082d4ecc', 821): '90ecae2cd7e3421012ad2ba97eb7fedf3f8c511977b526a75ec2e2e32e5cfd06', ('building__rom_082d4efc', 642): '787ed057fa33c9abd22572843349c7df9cae7f3efdd7c68c9fa190b5196ddd50', ('building__rom_082d4f2c', 644): 'ec0d61f4c699c51f67094d2000c2364d7519d2381bdcc80fcef8f7062bfa2912', ('general__rom_082d4b9c', 745): '07833cba57413c5e30f6fd50ee527399bdd77fe286b28999eb10324dbcbde418', ('building__rom_082d4ecc', 656): '5867e9b209b0570c8bc95d248707f486e82c1314897448660b83a8ba12bfc014', ('building__rom_082d4ecc', 660): '94fdee42035cc53177d0824fc01153d2f2a70c6187ab8b99cb1f66b71675dbb9', ('building__rom_082d4ecc', 816): '8e8b3c288fdd4f227c58698d3c20814b57edfb172f9939e536b5ad31090e5407', ('sevii_outdoor', 860): '22c5079c2f923c7e87047d243385b338dcccaaf4a5c6516f4260cb7b2f94981b', ('building__rom_082d4f2c', 646): '041dc9561b203f0959d1049f21f2189af0de769ca58a38d6e106b8a1f698e322', ('sevii_outdoor', 851): '69008a266a8302d264a94e21525bf50a7ffee60dbdc6c1054feba5033b46b846', ('building__rom_082d4ecc', 824): '721d6c6ccd0876a8e55d635bc3afd1eacf1ee832e8a8b861f60013ae365bcc5c', ('building__rom_082d4f2c', 674): '5fd140a418567e2b73c9a50a0e0940122ca88ee7b8fc03d7f996d2fd2f0e211e', ('building__rom_082d4ecc', 642): '308fddd37dd9a5e25b55f7cbf77fc073a1dc3ad902052dc973b707042dbab2d2', ('building__rom_082d4ecc', 818): '0677915c78ddf16c72d127ffb4fbefbee171d3f191d3e6d7dcbdb8e7c533f912', ('sevii_outdoor', 853): 'ae95c5bd01fe156ec4808bb3f21616eda5ebe1bc62a3215954caa358f1561f44', ('building__rom_082d4f2c', 682): '95be9d3a9f37eb45e77b82ccdf48b0aa7ecbbd4b89edf4cb197bd7ffb1244480', ('building__rom_082d4f14', 656): 'c9641540729e66f937cc8ab5e08e9981e069059e28c89f35568d7fea20bf25f0', ('building__rom_082d4f2c', 690): '1d665cf6ca164908d99c6a4a61f0575fb96b3a26913b1e9af0f911856ee0df34', ('building__rom_082d4f2c', 645): '30762781140a203a3409439fadc83c57d4d45a9c17a67caa9f97230b84a11da1'})
MANUAL_SOURCES.update({('general__rom_082d4e54', 693): '40d8ddcbbd0cb6a2534f0812628e7b6950ccf43803238534fac9989cf10c9769', ('general__rom_082d4e54', 654): 'cda6fa9c13965f254aa4718c9c936e3678dd28824385234e3945a2c27cc99c7e', ('general__rom_082d4e0c', 655): '7b56b654ab7abe0b74c4aeee62189d706d5f5d77f3479471dcacb59030c6f2c6', ('general__rom_082d4bfc', 655): '332c5c57d43509a62f7d648ceb0edb1c3e99da48986b9f50c9084c10bcd7a414', ('general__rom_082d4e24', 654): '4cdf55a52bdc7a239d1651e50c0475980af5dd2acc20b4e967d54a74c2094cf1', ('general__rom_082d4e24', 655): 'c3387921808575bd21f922f56383736a25612c16f147ea2d3a031554a35282b2', ('general__rom_082d4fec', 655): '219b2411f387368f65f894b4b3fd2e278a668fd273dc601d6237601c6f169271', ('general__rom_082d4fec', 654): '7a5c8ade53dca6be394d02d6e65a3726574711a6aa251d13d8f0f631b0adf273', ('general__rom_082d4bfc', 654): 'eb4e32c89820f6e24a1dca245bc79e381e57f0c316fd223592cbfae7f6e3ce3f', ('general__rom_082d501c', 655): '195c0db3cca387b212277f32afcebe8c2a7bceae9da11e59cd3f0b95ca3bb908', ('general__rom_082d501c', 815): 'db4870242f4cf0f0f4943d99bf09ef871f7060d771e3d9a1ab38ea424aee72fa', ('general__rom_082d501c', 654): 'f0049f8ac5af905d8bcf819d5a1e0f7cb932f074e701d3d1293d7d4363080069', ('general__rom_082d4df4', 655): 'abd36370123204ba2fc9fc14152593a8917cfa03e50a8d5ab20e8541b19faa13', ('general__rom_082d4df4', 654): 'c6ec3bf84a670208700ebc2138ea693d118ebad4b2ae20f3ed60cc56b9bb6b13', ('general__rom_082d4e24', 693): '9d7e700aa4f50c2fd7da3a8630b23a2729dd0c973ad8606e377c4820510ce246', ('general__rom_082d4bfc', 693): '1a332a2e6565bd2272bd5a3d3422debc551596b66bb62605bfc447b065249f3b'})
LADDER_HEADS={('general__rom_082d4e54', 693): False, ('general__rom_082d4e54', 654): False, ('general__rom_082d4e0c', 655): False, ('general__rom_082d4bfc', 655): False, ('general__rom_082d4e24', 654): True, ('general__rom_082d4e24', 655): True, ('general__rom_082d4fec', 655): False, ('general__rom_082d4fec', 654): False, ('general__rom_082d4bfc', 654): False, ('general__rom_082d501c', 655): False, ('general__rom_082d501c', 815): False, ('general__rom_082d501c', 654): False, ('general__rom_082d4df4', 655): False, ('general__rom_082d4df4', 654): False, ('general__rom_082d4e24', 693): True, ('general__rom_082d4bfc', 693): False}
MANUAL_SOURCES.update({('building__rom_082d4c2c', 273): '17fdc401c39312e29a51c2afdd70b7f9946f95a017c0f65654fbff87e4aea343', ('building__rom_082d4d7c', 641): '7a078c571c12bd62e28d2aa72abfc06ad7bc1a9236fbd1141eb65f797c75f51c', ('building__rom_082d4e24', 273): '17fdc401c39312e29a51c2afdd70b7f9946f95a017c0f65654fbff87e4aea343', ('building__rom_082d4f8c', 641): 'aa8c6243348fe2fc235a9a6826c1397c74b11b920c2ca14c7cc417d1d120ca9f', ('building__rom_082d4fa4', 273): '17fdc401c39312e29a51c2afdd70b7f9946f95a017c0f65654fbff87e4aea343', ('building__rom_082d4fa4', 659): '17fdc401c39312e29a51c2afdd70b7f9946f95a017c0f65654fbff87e4aea343', ('building__rom_082d5094', 750): '48bf7bcaeb9fb03d706acc1f73e1b3cc4b7b33ad3e0700c17eec7ecf15e23f9a', ('general__rom_082d4af4', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('general__rom_082d4af4', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d4af4', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d4af4', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d4af4', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d4af4', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('general__rom_082d4af4', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('general__rom_082d4af4', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('general__rom_082d4af4', 245): '1e57fa0b12a3712db37de7e42ec7bf57ca3ca2288ea12a491bc476f0bb586276', ('general__rom_082d4b0c', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('general__rom_082d4b0c', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d4b0c', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d4b0c', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d4b0c', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d4b0c', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('general__rom_082d4b0c', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('general__rom_082d4b0c', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('general__rom_082d4b0c', 245): '1e57fa0b12a3712db37de7e42ec7bf57ca3ca2288ea12a491bc476f0bb586276', ('general__rom_082d4b24', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('general__rom_082d4b24', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d4b24', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d4b24', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d4b24', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d4b24', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('general__rom_082d4b24', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('general__rom_082d4b24', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('general__rom_082d4b24', 245): '1e57fa0b12a3712db37de7e42ec7bf57ca3ca2288ea12a491bc476f0bb586276', ('general__rom_082d4b3c', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('general__rom_082d4b3c', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d4b3c', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d4b3c', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d4b3c', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d4b3c', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('general__rom_082d4b3c', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('general__rom_082d4b3c', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('general__rom_082d4b3c', 245): '1e57fa0b12a3712db37de7e42ec7bf57ca3ca2288ea12a491bc476f0bb586276', ('general__rom_082d4b3c', 808): '73a316576ead75eac5373fc0823dac9b6dcb308ffa972f1da747a4c87147654d', ('general__rom_082d4b3c', 809): 'cd4b607029bc20392a824e579446c71dadf9c0c78632c25cbf03ee974f07ed7d', ('general__rom_082d4b3c', 810): '500e964b38bbf93356e8c7d07ebf17ec243553c4169cc51cb272818625aeb31c', ('general__rom_082d4b3c', 830): '94a2826b80a1d200797d7a8b4d0c81bdc7e20a75b1f83a8972d6a8748a00d676', ('general__rom_082d4b3c', 831): '60c2b1a0e1a192a9df2490945a239fe13f217b79361bd22e7b56d46fdfacab21', ('general__rom_082d4b54', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('general__rom_082d4b54', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d4b54', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d4b54', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d4b54', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d4b54', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('general__rom_082d4b54', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('general__rom_082d4b54', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('general__rom_082d4b54', 245): '1e57fa0b12a3712db37de7e42ec7bf57ca3ca2288ea12a491bc476f0bb586276', ('general__rom_082d4b6c', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d4b6c', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d4b6c', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d4b84', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('general__rom_082d4b84', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d4b84', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d4b84', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d4b9c', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d4b9c', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('general__rom_082d4b9c', 245): '1e57fa0b12a3712db37de7e42ec7bf57ca3ca2288ea12a491bc476f0bb586276', ('general__rom_082d4d94', 804): '700dcee6cb5548db2655340ad38ccdb96b8fb601eb6428d449e105621f407d39', ('general__rom_082d4dc4', 648): '41b823908c8e3438d105d23c738cfe482cfa43b70b7dabb224bfb666eab69c30', ('general__rom_082d4dc4', 649): 'dbd3b895dc5970f25c8e649b6cdc4e29ea5f348f681a78ee7a1588a0f5f72916', ('general__rom_082d4dc4', 650): '83464388a52963fabc2682c32f34038ce7950d377674d77669a7c1b3920cd7bf', ('general__rom_082d4dc4', 656): 'e5f74dd199594337503f1d283874a360de772fb9675aabfe9eaa75d42bdca197', ('general__rom_082d4dc4', 657): '3e3c55746f3d9b429ec43fc45d8bcce8a136c2bcbb60f2e66a870599d69bf108', ('general__rom_082d4dc4', 658): '4d40c7a405108505e1ff2b6e66f3ff09ee720500c75fba7562d505a99c966620', ('general__rom_082d4dc4', 664): '1e4c3720f28ce8ff728b71d0d6832fb2d7b935dc19495890270ca2cdd593111d', ('general__rom_082d4dc4', 665): 'dbd3b895dc5970f25c8e649b6cdc4e29ea5f348f681a78ee7a1588a0f5f72916', ('general__rom_082d4dc4', 666): '006972deefdede5077ed75a6529e3faeae61aeda1791ebc21cc05094fa4b5064', ('general__rom_082d4dc4', 672): '4997fcc2e73a7a0c96df413afaf894a7167f68b411b46cb548345005e3d2a230', ('general__rom_082d4dc4', 673): 'f64363a7dabf55d98990204f95a3e41b0e88b1d3138ed71aa470127fa1067b27', ('general__rom_082d4dc4', 674): '4d40c7a405108505e1ff2b6e66f3ff09ee720500c75fba7562d505a99c966620', ('general__rom_082d4dc4', 675): 'de3edbcd77fdee5f43132b7ac3b1177a713222b2e65b27b59390528f95121c44', ('general__rom_082d4dc4', 676): '0eefaa04aa07a9945cbb78ddecb68ec7ec97d9477ad969dec94629c4c8ad74b2', ('general__rom_082d4dc4', 677): '00dbbfebda0c37fd6665143c54ec01b7cc3c4b919c10715082c1334c882c8f76', ('general__rom_082d4fec', 813): 'a00970a197d328b8df4cf3ed21884f9d555106f721b3b6536183f7f33e3c55f3', ('general__rom_082d5004', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d5064', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('general__rom_082d5064', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d5064', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d5064', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d5064', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d5064', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('general__rom_082d5064', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('general__rom_082d5064', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('general__rom_082d507c', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('general__rom_082d507c', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('general__rom_082d507c', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('general__rom_082d507c', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('general__rom_082d507c', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('general__rom_082d507c', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('general__rom_082d507c', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('house', 273): '17fdc401c39312e29a51c2afdd70b7f9946f95a017c0f65654fbff87e4aea343', ('house', 642): 'fc1e1232f424e6d6f8c11d03d8e531bb63d6bf079569c678e0c9e9e3f4b21819', ('network', 695): 'b2804146d65e16a0ad378985efbdd3beb273aae63cf781fea36e7fad55afd6fa', ('oak_lab', 273): '17fdc401c39312e29a51c2afdd70b7f9946f95a017c0f65654fbff87e4aea343', ('pallet_outdoor', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('pallet_outdoor', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('pallet_outdoor', 245): '1e57fa0b12a3712db37de7e42ec7bf57ca3ca2288ea12a491bc476f0bb586276', ('pewter_outdoor', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('pewter_outdoor', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('pewter_outdoor', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('pewter_outdoor', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('pewter_outdoor', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('pewter_outdoor', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('pewter_outdoor', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('player_house', 169): '58932ca20adf6cb593fde3cbdde180cfa70d7c1b298f037caea865b75ccbee7e', ('player_house', 273): '17fdc401c39312e29a51c2afdd70b7f9946f95a017c0f65654fbff87e4aea343', ('sevii_outdoor', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('sevii_outdoor', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('sevii_outdoor', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('sevii_outdoor', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('sevii_outdoor', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('sevii_outdoor', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('sevii_outdoor', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('sevii_outdoor', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('viridian_outdoor', 5): 'e53f902c44b53c9f0c2699f0ca86add368cafb2563597f30ee303f84ae45b2f8', ('viridian_outdoor', 115): '9296aab8d3054d7951f6683944b8a4d7e0da2c11fa90c2c70b27e5b32e08d6ad', ('viridian_outdoor', 117): '7fd80dbff582c2de1215fe47e8824ac977c0adf697b42835b0c9d6c4556af3c8', ('viridian_outdoor', 124): 'e65d49cbb3a4e160c399dd82f5bed8c7b8a437832c4e27fa0d39dad6cf5e9700', ('viridian_outdoor', 135): 'f5691dab17e4b76a8d98f238c67456179bd50712b1bb62ef75eddd7e87532d0b', ('viridian_outdoor', 190): 'dc001d1063b7a4f905230d5336383bf62bfeb87a0d5f10d7166f68a838316507', ('viridian_outdoor', 198): '04c673be4a9940043e6191d4e8f0021b9fa731b7c76c9e44d6d8a098bcb9b5ae', ('viridian_outdoor', 244): '631abb2530470cfd9a9f8da1242554bcd13201f16137b3ca18abec7b79991466', ('viridian_outdoor', 245): '1e57fa0b12a3712db37de7e42ec7bf57ca3ca2288ea12a491bc476f0bb586276'})
MANUAL_SOURCES.update({('general__rom_082d4bfc', 641): '7c00b111759c0a0f43147fb3ff3c4965087813bf076f7de5d3787de05c2d8ea4', ('general__rom_082d4bfc', 642): '3fcecd895f184b97e1c42724b8aea118e763dca2520dcaab07a8383d0775db59', ('general__rom_082d4bfc', 648): 'a530ae707e3a661089709786bab783a5aa772e9549f5b18eacb2271b9eed8e85', ('general__rom_082d4bfc', 649): 'f27c6ef5201650d485fe4bea1713335613560622c88e12d9cfbe078bdc34362b', ('general__rom_082d4bfc', 650): '33f9738388b4d2b9d1aedf5ce81d1bee98be87a308fbc6557b280a4b88c5c0ee', ('general__rom_082d4bfc', 656): '03f761690b9e273099f5878290ebb82836361801feb6c51b01d6d81ff9b88018', ('general__rom_082d4bfc', 657): '84aa5718b8441016308f1fc3d738b9a79e325484a752c80ac1ddf04755360e5e', ('general__rom_082d4bfc', 658): '10617f3b651258211e9c9eab35683d56ec190104efeec96e46dac81d5940609f', ('general__rom_082d4bfc', 664): '0b52679ed06f96d7d893360b51253b182ceb0f98b349d828c8d0fd5ea8959bf9', ('general__rom_082d4bfc', 665): '4ddf9fef06746d6adcb7a3398f35062527e4f5d3f150152b33b97b8e3e593e35', ('general__rom_082d4bfc', 666): '5655ec4829c3219cf398f264765a38ac38c3e629fbc45754e8dd4469cfb127e1', ('general__rom_082d4bfc', 667): 'd24cdf9e811a2b0b1ac071679cc3f19f6fa3ff2a919108370fdd681969f45619', ('general__rom_082d4bfc', 668): 'e4fef1625119b6a3f390d5ada5ad70b15ef0cae28d24e26c0c7662d7fd8e2853', ('general__rom_082d4bfc', 710): '4537598c20fc8d7ad7255a8d4402579f5cab00d92f9f4e1b632d32b79f8e9a0c', ('general__rom_082d4bfc', 711): '2174de6e5c14aa34ccbb6e83b5207107cb65bc19dc2efb3c559fbb83575a1d5d', ('general__rom_082d4df4', 641): '5fc0ed6df9e6909c4fb41951ffdc21fab382561e183b2482311260a1d186de35', ('general__rom_082d4df4', 642): '9df58ba0413fb9131ed8afbcbd59b5f6fcd9103b3d9c25e3d3247b54f5c93038', ('general__rom_082d4df4', 648): '3956a7d76608179bff0892995f562da13521d6999b6e57d6e2124a2d811135d7', ('general__rom_082d4df4', 649): 'cd2cdecc3c74a9789e96f4e555691ae9331afe019ed1e1c45473768a49973f8e', ('general__rom_082d4df4', 650): 'bd5e3112678304c2b3d17afaafab104589dc6362ad94763cf174780a0924baba', ('general__rom_082d4df4', 656): '881745e77c53038a116d679e293423df9563972deeace66f05d23beb8dda1580', ('general__rom_082d4df4', 657): '088149cc561639b71b34181fe2fd14b3cc00ea41860d7755975b7695c0bf3bc0', ('general__rom_082d4df4', 658): '8faec2167b26801890ef58bf1d252de4ae1b9a9ea1adecb8f8aa972ec6d92841', ('general__rom_082d4df4', 664): '916fbb6d48689fb28558fd2bdd957624ba5cae1fc81537c6a88567af6211dc6a', ('general__rom_082d4df4', 665): 'e4eebbed04732fcbee7ef303db4648c09e1617a3241acf4f67a1a79f5c910512', ('general__rom_082d4df4', 666): 'a9e3cd596f5af11a4f35e3ce9b503329dd3dcd38804924f1fe6885adcc25fcee', ('general__rom_082d4df4', 667): 'dc3f24a4f28fe4b49248698527071dc7c86e4e97e79caa789fad2544b4665979', ('general__rom_082d4df4', 668): 'fcc1e0b960eb98e2598f50c706ce819cadc6a8687e97eba7d71544e12513c786', ('general__rom_082d4e0c', 641): 'fddf002a22f06102111aa5133db25fdae8d3e129eecabafec7eecafe907ec543', ('general__rom_082d4e0c', 642): '635ca4108be6f191205621a3982240aa391403d4c9e15880added1865935f600', ('general__rom_082d4e0c', 649): 'f01e9d4d1b0a093b155d20652cb09c84fc8b4e5fd032967650b7a6c4f450041f', ('general__rom_082d4e0c', 650): '913005b38bbf061daa5d2532410dd347e0480282538190577db58c22ac5fc0bb', ('general__rom_082d4e0c', 656): 'f578ce498ef11c5cdd283880c58aab0cddfa662dbebe63ecff0893a367bd7933', ('general__rom_082d4e0c', 657): '372ff3912e41ee1c2e554b839e3bdd9bb5203dc4e50639b4298101702b85be91', ('general__rom_082d4e0c', 658): 'be08f0a54be61de33665a41fefad1b53a6a7598f64c9ff72c73a5ab74572f730', ('general__rom_082d4e0c', 664): '48b99f65a02e06d17dc9d4570c77604382733b47090cfddc754cfa5ee66b49ed', ('general__rom_082d4e0c', 665): '765b20af278e52b75bc75bc30afa5251727fdf2dc4ce93466013ff709c840a53', ('general__rom_082d4e0c', 667): '746f202fcd8ba1fed0cd2d84a9c4d71ccca57dd98aa0e9103a479dde19db2e8f', ('general__rom_082d4e0c', 668): '6fd44f0eb02c56f9cdded17451157429b0ca6b6943a7d07a7886a5fe1f4a2aed', ('general__rom_082d4e54', 641): 'ae1228caa581a56290f5d4b70b310a2f26a173dd3a1f90a6a95a43abefcb3264', ('general__rom_082d4e54', 642): '5b7ea859bbb62f4e037857ad67d988e237aa9097ed9ec8a3446f6a403eb7f6f4', ('general__rom_082d4e54', 648): '6a5e6180555196b460f93f354a6417391a81c4e2c2e0f28cd3bb973e71db4fb8', ('general__rom_082d4e54', 649): '3f8912476e43be4ad84773d7ff60e941c42b371110dd3066615ce3d3f018bef9', ('general__rom_082d4e54', 650): '141fdaf2989b4b4897261c7c9ff64f902faa0fdef33b442686e92fdad36338da', ('general__rom_082d4e54', 656): '62086d5a4123a134df71b10a6c9fc2134c6b28904dd5e20dd9fea5a160f71870', ('general__rom_082d4e54', 657): '3147bf37dc6147bab6b10ad1f70b58ce85f44570577479b4d689590e3c95b316', ('general__rom_082d4e54', 658): 'e14f9da246329d22bb604850a1d5d3413ae4978e6f17ade7a8b294c908cb3195', ('general__rom_082d4e54', 664): '27c0c8e64d8e992d3dfb979d93a82f0e035c21eba8ddd86ba334b7dbfcef1b3f', ('general__rom_082d4e54', 665): '6a39919fd70b586bd343d01217828a7d2927fe9978ee2c6461f6b34aa1d10fee', ('general__rom_082d4e54', 666): 'c2dd8f1635017e175720b108655d65ba26591bbd5ae8b473d5b81024d067a75e', ('general__rom_082d4e54', 667): 'e867ba8960b76c6570218da370aeb3a935ddeec5f95c81bf3b4d7bdae00fadff', ('general__rom_082d4e54', 668): 'a5f5f92e6d6cb341e01099fe88e881b3ae50e03a52d0096a081d5fc2f46bbbfd', ('general__rom_082d4fec', 641): '09f676ca0709d640fc6d16cfbce65f5fc5bbc27fe47f14146f5d7f994d06f58a', ('general__rom_082d4fec', 642): '2da66cbe006ff825e957aebf0134da8f3fa0a3ae6ea76fb8f419a0666fa97ac7', ('general__rom_082d4fec', 648): '9c81a6333c325e58ccc73a5c7a9bd85c44340805d7c90f4f15efc8466129d34e', ('general__rom_082d4fec', 649): '45311f709b779b3042c85e5dd810769fde3c086c8e365528d577b80e0df08107', ('general__rom_082d4fec', 650): 'db4786d7be71982a7cc1e5e2ef3eeb01d59105600110048215dd0265df77ae00', ('general__rom_082d4fec', 656): '5f9c3d2bd9a9f614b50097496cc02f959633a671809335b2d734f444d587a0ac', ('general__rom_082d4fec', 657): '9f584d3f2cd153232144062d098960cef6b13269e88214199a9845c75ef9c5f5', ('general__rom_082d4fec', 658): 'f07c495addd335a2d0457453fb0325aa0c1147e4aa394ca2b190661e8d5181ce', ('general__rom_082d4fec', 664): '74b84e79ffb6132bb6cb0108797e18242490d3e138cc52bb313b4b9f9613262b', ('general__rom_082d4fec', 665): '40b386eb9a1bb66eef3d868a8975e1020b5c1675abdc53e9579b34788fd27d79', ('general__rom_082d4fec', 666): 'eb3b939161f8c10911c394514fcf0b70515d442492be4dcf59892d3ab1218a11', ('general__rom_082d4fec', 667): '1a6868188cde2560f329c47ec8cae06eed99696da4c3b7621e873419ed4b7a35', ('general__rom_082d4fec', 668): 'c618ed22e42c7535be04b80b2b33e9807984413a5803ab8aec6fbcd52b481bdd', ('general__rom_082d4fec', 710): '05afb6d27bb46cb21e7a8fd945461efd19ef1073328db03cbf82ba1b15c65572', ('general__rom_082d4fec', 711): 'fa7608b93fcde380ebaabbebf8913b503f7d36312947838b9db0d465cb499f14', ('general__rom_082d501c', 641): '2641db391478ef5ddf91c8a54ca6443c638437b14aadd952d61a63c076d8eab1', ('general__rom_082d501c', 642): '2629b96216ee616f52b279bef8a385ec5d5eb8839935816fc658f93937e485c4', ('general__rom_082d501c', 648): '448959f06e5b92e2740a9d7972a06b6cd37bf82e29cf579fcc244b5b68634bb1', ('general__rom_082d501c', 649): 'f8660e5c34856ab31222952e8883ff0d0e39d060878ab025b7539035889cae0a', ('general__rom_082d501c', 650): '5bf8c0c614aa3b5c6aa3477355721626c4ff00975cbca0467c76d7e115883aea', ('general__rom_082d501c', 656): 'e9f1a6a2bf4612670c29510c4c6ad365d0ab8e064dc0e80ade78a7805ae81a98', ('general__rom_082d501c', 657): '97441571665b43bd651918fe3438220ca73eca35e44d8f6642b0b961def4e932', ('general__rom_082d501c', 658): '593eda4266d63b39d881c92f61c32a9e63a346cf5158819238cd3180d583d23b', ('general__rom_082d501c', 664): '9e381bd9455a1a468c0783302374aee886c2f98a04e82d65573683a8a769f89a', ('general__rom_082d501c', 665): 'eab6eb288e29c2f237bb0c4dec5aa5a9500bf9d2fec5461c27187470620730c4', ('general__rom_082d501c', 666): 'd137e160dc8a2e12bff281950165ea1308202b3f48c10f307d59598e8a4e66cf', ('general__rom_082d501c', 667): 'ed6c3beebf79b62694d7bf07b2fc3fbbc0ae640bc0c3ccac197467a39c31f0f3', ('general__rom_082d501c', 668): 'c3e2d5a71dfd9c8ac1aed052d38ad4be93e5292c8493c29d72d7c5755b43abf5', ('general__rom_082d501c', 710): '4e943e1cf9d6d84a9a0549969b991f6e475795ef6898954b29b9be79599a82cc', ('general__rom_082d501c', 711): '6c9a60f8e75c80dfe71015af397da8210be2826acf74e04f903ce7bb32489235', ('general__rom_082d5004', 641): 'fd03578cd3387fc4e59605ee242e47d68b204497fd538f50855d3a4be940b493', ('general__rom_082d5004', 642): '10e3b3bc2099a330a8518d76a3f8dbbe5eb64669aca82ad278b1dd496ffd6678', ('general__rom_082d5004', 648): '361f894e7e89fe7a72f976511e0209029a493bf90a1f5d5e50a86835521ecd5d', ('general__rom_082d5004', 650): '614efd8e0ea7051b99ccaaf8681734ec2bc9be248ab44212245ebf2798b7b30c', ('general__rom_082d5004', 656): '7b7cd73f4b6ffaf5c61e4dc9a1e45e830ded31788e1d7aef77e58116284e712b', ('general__rom_082d5004', 657): 'c108e126abae4084c3d288ef5694afd14f850471663d797e4075e1adb947c60c', ('general__rom_082d5004', 658): '5d18e28168e8dbb63143b5fa9238ddec9a2e5fe676e197f775ea18464fd3f990', ('general__rom_082d5004', 664): '83f19ae4bd58a05a91a4b835b26df135000f7445a550c794d30a9ff047a3f728', ('general__rom_082d5004', 665): '5f46613c9b3a7797e944227f68e2d7778f4240a396feb28065d29a52e2697b98', ('general__rom_082d5004', 666): '51a42ac39f1d5d3752e761fdd46204c320cb8ec66870c0d44d8508ce3d5475b2', ('general__rom_082d5004', 667): 'd64b2525382e73a648db6f183a0ab6b707aec4980a03235ee87a204cb9562a1c', ('general__rom_082d4e24', 641): '4535a2259483c690a07749f1582426413d341871f163bc1d33f9dd1987a70a18', ('general__rom_082d4e24', 648): '99fd32c0900e53b2a448a34d9467a180ef9824dd95e693562ecf20c82564134b', ('general__rom_082d4e24', 649): '80f8ea201f1cee0eabf2188ecf2fbf5ba46fdd8f8291039027cbce5a93865800', ('general__rom_082d4e24', 650): '6dd72ce9af8fd8b8023095cb8e98c52317c95d772fe7d914cf3d9f5509937583', ('general__rom_082d4e24', 656): '3a222828efab8737ec09a31829a36e14633580545ac1655297547727c77bfc28', ('general__rom_082d4e24', 657): '78dc72b50a545a432c272b2bd0f45d8448d2808ceab67e5954e89eaf44fa8856', ('general__rom_082d4e24', 658): '4f4c515be41df4d6baf18b663bf78ba00a148ed688ad9e5c10b8cb9a700d69bd', ('general__rom_082d4e24', 664): '240d851ca3fbae49bfbe8233261c45808cef9be44b6c6ee3bb5be1ff954b84ee', ('general__rom_082d4e24', 665): '743a691d20535a318a89979cb505e13e50a307671f6635c006128a0ae5851706', ('general__rom_082d4e24', 666): '05ce0e4dcda3c943e7d2bba41b67d49410f0a6ae16f679fd4bdd6dfd0a73cb1b', ('general__rom_082d4e24', 667): '37679f2cb39778dc8e7c34ab49e98f51ceb245d5729351868d78d6a057f2b307', ('general__rom_082d4e24', 668): '44cd94c9c10ef4d5b7c9646951177aee3334f136f42ea9f6094b95ef70f01304'})
MANUAL_SOURCES.update({('general__rom_082d4b54', 756): '516f67d43df0a17dbd045017439d7199ffe98f3a21cb1f8e81675536b6ea1989', ('general__rom_082d4b54', 757): '7896cdcd3eaa3511abf2c60aa8bf0ff212b438b32893e650f0f4f7379ebf8b1a', ('general__rom_082d4b54', 758): '23ff82ee2c051221eaed9b3b3de79ab32666539ee20f88d4a2e4644565784b41', ('general__rom_082d4b54', 759): 'cb9ca4f1962f5c52fe1fab34a18bd134b5a7d1e89ab3306d9c51a2b9ae416fae', ('general__rom_082d4b54', 764): '946a10bad6209032a9192ec7eb878488d9190e500981a904cf02d29b8a36a1f1', ('general__rom_082d4b54', 765): '123ff2990fe58db14de514fbdc52a35d9f2670a1a9f45befabfffd7c8953bd2d', ('general__rom_082d4b54', 766): 'a6b4c29e9425258e786bed1b520ff5f611f3e7fcc6e413475d704163d17c22f9', ('general__rom_082d4b54', 767): 'fa2a2cb79b1f4d28a7b2b8035ac70b9c9382130c288ba8c82e8493bdf9c01266', ('general__rom_082d4b54', 768): '4c3015b809d8fce1646b0d6fb1e3c8ca1cb3d1867c5b6c827c7adc13958eaa81', ('general__rom_082d4b54', 769): '3ca41cb31f994536b5fe66db593003875d00a38ca9d4aa9e57c79d34b6ffefa4', ('general__rom_082d4b54', 770): '78fe198878bd1e0dbeb4ae066ccc68627f3f33a836d14d008ca3c659a0217382', ('general__rom_082d4b54', 772): '7e8dd5b15ebc84e76afc461c23fc0e2afa6866e24ba9b296e6f2953e650c7ca6', ('general__rom_082d4b54', 773): 'd34756f57421399548e066565c187ab1e22584c7c74948cff92f02c38ddbce76', ('general__rom_082d4b54', 774): '3af44a76b29738c200dd34110c88408716db8a7e9c1cc104aa310507f25b7696', ('general__rom_082d4b54', 775): 'ee6f5810eccbbf6e2ff5cffe43a411d3077b461e1654aa8650175af57c881d52', ('general__rom_082d4b54', 776): '7e0b1be7e3f345fee938f50b172d4e8b5e1d93d007881138aa6958a35a6a1ce5', ('general__rom_082d4b54', 777): '89166176def6a40aebc0ce4799e45f64af9ce265db798fe61b82e76ea3775947', ('general__rom_082d4b54', 778): 'a89f66c2ecff9578c0c0fa2c465a63702f5ab31b5b8bd715525a87f074e2e3be', ('general__rom_082d4b54', 779): 'f54e6e0180070653c617a4f1c87ed114df674a24eb93ed19e889d4e7f911f0af', ('general__rom_082d4b54', 780): 'aab71cdceec6dd2386031fd14d8fb67383638c59f22adf3cf00bd64145b422e3', ('general__rom_082d4b54', 781): 'e10e07bb13407d2cb5b100f766a998ed4b64f7a1f263041cfb6af768c6db091c', ('general__rom_082d4b54', 782): 'fffff9cb030886693c9a626e196e81019258e9099423ac4203b4ec93464dad61', ('general__rom_082d4b54', 783): '1a372ab45d547db8958ac130e3632c792ffbd8eb50dd7008e6f12248c5563bf8', ('general__rom_082d4b54', 784): '6e2fc2c309ceaf8e0e0cf0c56115674aaab00870400d9f82209c14936a530441', ('general__rom_082d4b54', 785): 'd2ea94ccbbea59d4deee1df459cdfe69f436126ff7328ec7e3b75b1a54b9464c', ('general__rom_082d4b54', 786): '935d6aee0cacfe853e866d4392dfe07669794199e1629d2aed33c473f2e78af0', ('general__rom_082d4b54', 787): 'e10e07bb13407d2cb5b100f766a998ed4b64f7a1f263041cfb6af768c6db091c', ('general__rom_082d4b54', 788): '1a372ab45d547db8958ac130e3632c792ffbd8eb50dd7008e6f12248c5563bf8', ('general__rom_082d4b54', 789): '59cd910de00ba1da7bb241f82a6ec2d38af771e89b85dce80e7142dbcd0dcf35', ('general__rom_082d4b54', 790): 'ef2100faf146d22daba326abd136ebaac7f2b7fb39d9aecd6c2029e06abbf032', ('general__rom_082d4b54', 791): 'fb6d73adad0c387b14728e23be78fe5d4b4ef57fb0f81b8fcc6719e2368bb118', ('general__rom_082d4b54', 792): '9d4dab6dcd87f3d51ea8b1ca8a6ca10d891d8e491d1fe4111f88112c37d540a6', ('general__rom_082d4b54', 793): 'b3440c3c0998590f25d873e2d9aec815f8d5516b4de9ad310e7ee17e606e3680', ('general__rom_082d4b54', 794): '10b7bd202fd157d3c6767925bfae887375a40e2662b69b205b28a64074be2f06', ('general__rom_082d4b54', 795): 'cdd25f306c55ea49bb42262962f4cd58b21e6e096dae8fa30ea5d1d976f24506', ('general__rom_082d4b54', 796): 'aafc35d535679fec50e9fbefb318bb1208569e99c0e9b42cf5af3c6c89338d07', ('general__rom_082d4b54', 797): 'aa377de0be715a21d9ac8d97c4e233825dd8e20349125e442eb66293cd00a36e', ('general__rom_082d4b54', 798): 'a6b4c29e9425258e786bed1b520ff5f611f3e7fcc6e413475d704163d17c22f9', ('general__rom_082d4b54', 799): 'fa2a2cb79b1f4d28a7b2b8035ac70b9c9382130c288ba8c82e8493bdf9c01266', ('general__rom_082d4b54', 800): '150d063c290daef89f94fb3be1f370d5ca3179bfafbf62915dd00c9440560a7b', ('general__rom_082d4b54', 801): 'e3b55521a64638376400c396dea2fe950b9fd37934b91d5877002429392f2dcb', ('general__rom_082d4b54', 802): '946a10bad6209032a9192ec7eb878488d9190e500981a904cf02d29b8a36a1f1', ('general__rom_082d4b54', 803): '2bae731a2af879513a43f8e925e27c85050ff0bd590e11e770e30fa31b1e26cf', ('general__rom_082d4b54', 804): '1562f30ab610890ff67506fd8eecf41799fdf4d33b813a0e09900861aa2bdaf4', ('general__rom_082d4b54', 805): 'eb9e6c3de8af0db3535d815855d83d33fd15fc1142dafbe0268f455728557ca7', ('general__rom_082d4b54', 806): 'fffff9cb030886693c9a626e196e81019258e9099423ac4203b4ec93464dad61', ('general__rom_082d4b54', 807): 'ae18b7c5d0e8c6d181239e6a9445ce5014ede403505dd41e70989a9b5419f2ae', ('general__rom_082d4b54', 808): '9cca20847c395979b2680ce1a9796b4d8dc2db7f94e840c54dd9c5151c5b392e', ('general__rom_082d4b54', 809): 'c8057e9a1398d1f01d897985efdeefa3ce7b04a1310c8b035ca3ce97cc3dae65', ('general__rom_082d4b54', 810): 'b33623a2b4577a1ddb8b6a92f6201ad75bbe509a15f97381ca6498ad8cabd875', ('general__rom_082d4b54', 811): '1e1e794ac8fe0d725d25ce6ca6e0196c498a77b644566c2129b62513043efbe9', ('general__rom_082d4b54', 812): 'c8057e9a1398d1f01d897985efdeefa3ce7b04a1310c8b035ca3ce97cc3dae65', ('general__rom_082d4b54', 813): '16587ca7552fef095ba5059ed58ffd0677ce1f1242ad2bc089ff53cdb1c50c12', ('general__rom_082d4b54', 814): '7afb72e5c95490b5fb42c0e4970c8db49caa39ddf46aa8cad3386756d82cfad5', ('general__rom_082d4b54', 815): '86933941a688b595bfe069fa082bfdd0edbe026165110fd5560016cc48b889f7', ('general__rom_082d4b54', 816): 'cb3326f31bfeb32417ba7386580ae35b4395bae233a466938833155c5519a1d3', ('general__rom_082d4b54', 817): '719da4bc7a3434214a0e0be38d6edda6e6af1b87671a24886933edfcaaef7acd', ('general__rom_082d4b54', 818): '624239c60845e334ad73c5804b1403216c1dc5d445165604e3bbf9d1ef2d5f9a', ('general__rom_082d4b54', 819): '3a8b116670b5463b8c5a86210573661878d6db316422310af0e247a4557ee4b5', ('general__rom_082d4b54', 820): '087b85fd0cc8f3976942f6c00b38eed806895504458064fafc75e2c9ef40e3fc', ('general__rom_082d4b54', 821): '4c585b6f5b784be5ef800c681a5531af29c0f229674e79c21446e9bf94491102', ('general__rom_082d4b54', 822): 'ac6204652623132e716a63def8c52661f1acfddaddf712c39e0b69ff1810b9b3', ('general__rom_082d4b54', 823): '0f17ba453d4ce84237e1a4f5efab581b1d7c91c06edef31a8b46d5e90b45916d', ('general__rom_082d4b54', 824): 'f588e255e4d37f8e6027008ec61545b7517fc21e2c8c60ec08fcebc2a7ca3617', ('general__rom_082d4b54', 825): '0a7b2a89a3d78aa62f0f3a308fe88c7af0d791bc3c066727190cf89447b05eac', ('general__rom_082d4b54', 826): 'bd960729d12facde3f8b957a9325020206e83411ad00a1543e916b530a22cc49', ('general__rom_082d4b54', 831): 'e9b8aaec344608b28133711f608101c305b7f79413797559dee43d8d789c37c6'})
MANUAL_SOURCES.update({('building__rom_082d4ecc', 680): '01634be638fef9e2a976cd84406851cc32d921271a84f4d392d8488461daeefc', ('building__rom_082d4cbc', 651): '01634be638fef9e2a976cd84406851cc32d921271a84f4d392d8488461daeefc', ('building__rom_082d4ecc', 672): 'bbefe053fc1f5a06286eb525d752bb1b0bd2e2223c984428b3e28d5c2b4dc411', ('building__rom_082d4cbc', 652): 'bbefe053fc1f5a06286eb525d752bb1b0bd2e2223c984428b3e28d5c2b4dc411', ('building__rom_082d4ecc', 655): 'b762e924cc7a9b54d35446c54c742f7a7de02d5315ff1f0b187dd51f7101b527', ('building__rom_082d4cbc', 653): 'b762e924cc7a9b54d35446c54c742f7a7de02d5315ff1f0b187dd51f7101b527', ('building__rom_082d4ecc', 673): 'ec290eecfb95cd33b8aa95dbbad4c344eb714a4e4e28d3e4bea6d60ce9de6453', ('building__rom_082d4cbc', 649): 'ec290eecfb95cd33b8aa95dbbad4c344eb714a4e4e28d3e4bea6d60ce9de6453', ('building__rom_082d4ecc', 681): '408396966eee9b4b192cfe49a0bcf1b878e26127db3f8c2c8a91dc0708f9fbe6', ('building__rom_082d4cbc', 650): '408396966eee9b4b192cfe49a0bcf1b878e26127db3f8c2c8a91dc0708f9fbe6', ('building__rom_082d4cbc', 698): '44516aa7f8992909e468222e70de5050ebb6218398016895e09ee06d66c49c68', ('building__rom_082d4cbc', 699): 'e2c2c9804f92c3bd481787978ac2dc154e716b06ebf2c9346d1a10e7b96f885f', ('building__rom_082d4cbc', 700): '3fd2366a119e2e20d54112eedf17ae40cd8f4f2ffca2b068494c90c75ed5e83b', ('building__rom_082d4cbc', 641): 'adcd20d87bf35cdca945fb6cc12ec55c46f4296fdc63b3a622798531b6b2df71', ('building__rom_082d4cbc', 642): '62e04a963a6624500b5c911902e97ad8eec70304da90d4d021479e30866211de'})
CLINIC_POST_UPPER_BOUNDS=[[1, 0], [1, 0], [1, 0], [1, 0], [1, 0], [1, 0], [1, 0], [1, 0], [8, 15], [9, 15], [8, 15], [9, 15], [8, 15], [9, 15], [8, 15], [9, 15]]
SPIN_SYMBOLS=[['building__rom_082d4ecc', 680, 'south'], ['building__rom_082d4cbc', 651, 'south'], ['building__rom_082d4ecc', 672, 'north'], ['building__rom_082d4cbc', 652, 'north'], ['building__rom_082d4ecc', 655, 'stop'], ['building__rom_082d4cbc', 653, 'stop'], ['building__rom_082d4ecc', 673, 'west'], ['building__rom_082d4cbc', 649, 'west'], ['building__rom_082d4ecc', 681, 'east'], ['building__rom_082d4cbc', 650, 'east'], ['building__rom_082d4cbc', 698, 'stop'], ['building__rom_082d4cbc', 699, 'east'], ['building__rom_082d4cbc', 700, 'east']]
LADDERS={'d11e24cdca2276136db5b31c3a4bae823cdaa800da7664d0bd86319e753b1c51': ('up', False), 'e433258625261065da2c03744590f4b4b8d5372d14ea5d02c85ec855e9eeb269': ('up', False), 'f40e7a2cddd9dd91e7629c97ac1daa4b6d1bcde70c411446c217898e3bb0d4ea': ('up', False), '57f1496016c6e073e9c28b8d984c8b1afa9852c46713de727218cbdcbfbf6be0': ('up', False), '88f43e18f36b8f4cd2bfbe1c3ed7b52b495e50ccdee9cef5b9c6ff434ea04a6e': ('up', False), 'c4af3d7d42a9ad0454721e51ad87da6903908a716c01eae6e30c756d8e7f8ff9': ('up', False), '8126b235022a27b1d34b16ceee3fc413b1d896c4744ecaffc1eff0787db034fa': ('up', False), '6ec2fa915b1e6171949094b5194646701c2d52d540d8adfb2c9391da010603b6': ('up', False), 'd351869357102ee2a75964ec36ffc8e03411e8b44c5af338c4d085c0c22c89fc': ('up', False), '5f5f38c3fbc2c573959ae3b6f3e3ca3d316ecde48d38281892abe90c182b3032': ('down', False), '05ccec5bbfbd957339f9c91b7a9b0468af9ea78147d3ad99f471cfbee5b19985': ('down', False), 'b0f0ae94476021a3490db428c69482a2c67f59da0922860052c9392e19384cb3': ('down', False), '234f9922f3a9b9e2c99a9b609ba1e8745eda63e2833b5483ec6681f9b8862ab6': ('down', False), '5c425386294c1ab32f81495ee28d099335fb0b1cd0f3dce705e87a38eacef5b6': ('down', False), 'a46e9b01fb3ab78a44c04dc076ad31684cf7063587135d636054497b83825abc': ('down', False), 'f6a7fad4c8bd44d8d8c80417b7e15028ac53cf7ec3581e125ca178e40fbd98ce': ('up', True), '8785980e06e91b07836c20c7f2331abff7744316248abfccb3f50154c87c21d7': ('up', True), 'f2b4d5fa0e27c6a8e7c52823178437c6a5f4bb6a8d979dcedc6cc806bdc919d9': ('down', True)}
SAND_SHORES=('f67d83e5b660a16b7d3cc30123245ca2ffee975c39c81d3fd73ac7e0ced4b969', '532b23f7926aef7e0e36504b60d789b2ad53eeff5512046bd7299b4419676130', '9900d42d53bf929ed5571574bc45ecc6179e96a287df5ba1b24baea069c37598', 'a4211b82b26671179eb6e09d2ce3c176ea827b55a0dfcb71d20f0fbb9d17efc7', '801d9738055f30d881be4b90df921d73df8856ad90818deca31feb0c71d46eca', 'c5086eae153888995e60c1a87c64d5324031c3b1981e466616518b3f5b020112', 'f8108c99baaa2e517827f31f0e9edfcdb5adf2bd5373bbb0c98c9108cbda0e8e', 'a400ca9c205e7b5e0fb1913458b31e47ade0ffa5e4d097c5e24ba8647662219e', '6ba32d980c3a407ee1061debc9987cc14f638bd5f53fd2ffc549af853fa1eafd', 'a850a19d30273ecd8aa45985d0f40e012953a3e2046b39742c9bc180f1b966c1', '4e27abd77e96fb47efbbe6674f4ff4f3ed551426a702ecb91d79667a3e286336', '358a973a24a47c71a0b00aeb9c67fccf367a0696290ac01e272509b6736cb555', 'd71f356e4a600cd1b679ec1345817cb5b7645262f418f6a3e76ea132074281f1', '23cebbdb7abf7b928d9afe841201f4e7d474aafe168364e8bb02ae9dbef8304d', 'cbbb76f708f8b16508b67ee5a9da874ed78ec4ef9969708668232e2978128017', '0518e2688f23e7dc0aaf4e0bd6ea73f8619cdcd7f2a278c1e1d68028239222af', 'de7fb6830badb31ef132791a4584a00aa19f143873af34740a54ef763a0c3418', '46143f42ab52c3ebcda95ddad15fbddca346b97cf2087cb81d7d4d268685797b', '31687f79a49b21d9e2594098c79637893b21af4b0bc713a04444e2c57856014e', '158215e384e3281476ddd457a4eaffe5cb52edb98b6fd97e5ef6a137e1c07919', 'b514b1649fb927d607d78055350c8de9237c64bacddbf218ca2d451da9242b24', '3bb0880d2e064659c28b72571b5ae2fccbff3ff1a66cc730eee65594f8493b2d')

FOREST_TREE_BOUNDS=[[6, 23], [5, 26], [4, 28], [3, 29], [2, 29], [1, 30], [1, 30], [0, 31], [0, 31], [1, 31], [2, 30], [1, 29], [1, 30], [2, 29], [1, 30], [0, 31], [0, 31], [1, 30], [2, 30], [1, 30], [1, 29], [3, 28], [4, 26], [6, 25], [5, 26], [4, 27], [4, 27], [4, 27], [5, 26], [6, 25], [8, 23], [10, 21]]
FOREST_TREE_HASHES=['fec47f4ee792556f11cfc88a7ba0246fe8ea8111ee212932f4e8379e9a5742cd', '4994055158cdf69bea25c11a9f2ed0d90149ef3720e38c0be5429f81a03d884e', '98e978b568681465462ee54a6fd244661c183bf1c706963998904bc0061585db', '2b3fe30be1d5ffb4c48abe334b9a8fa5f53e99e3570509c9bf831b6698848ac8']
PARK_TREE_BOUNDS=[[7, 23], [6, 26], [4, 28], [2, 29], [1, 29], [0, 30], [1, 31], [1, 30], [0, 30], [1, 31], [0, 31], [1, 30], [1, 30], [2, 29], [3, 28], [3, 27], [6, 25], [8, 23], [8, 22], [9, 22], [9, 22], [9, 22], [6, 25], [4, 27], [3, 28], [2, 29], [2, 29], [2, 29], [3, 28], [4, 27], [6, 25], [10, 21]]
PARK_TREE_HASHES=('b29b9d5f82dca9653f1f3147b8e0483a321f9fe17253f6c955a9a9d03706b070', '216489f916c47672f00b9c64a652d24594256ad55f71b7a1515a0e65dd847f3b', 'c10ad0fdbc0ec51b431d5d29dbacd892eb7a377aa6bc7fd1248c035c598006dc', 'd52ad6bad771aaf71b12d4f40bceb1bf133f66c7472ea85c058c0c7d88edd49c')
TREE32_TARGETS=[('firered', 'general__rom_082d4af4', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d4b0c', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d4b24', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d4b3c', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d4b54', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d4b84', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d4b9c', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d5064', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d507c', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'pallet_outdoor', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'pewter_outdoor', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'sevii_outdoor', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'viridian_outdoor', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d4ad4', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d4aec', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d4b04', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d4b1c', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d4b34', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d4b64', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d4b7c', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d5044', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'general__rom_082d505c', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'pallet_outdoor', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'pewter_outdoor', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'sevii_outdoor', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('leafgreen', 'viridian_outdoor', 28, 0, '7019ecc57b8340f1ef1eaaef78b65ea249d8dda61104a62038350c22fedb4d72', 0), ('firered', 'general__rom_082d4af4', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d4b0c', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d4b24', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d4b3c', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d4b54', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d4b84', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d4b9c', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d5064', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d507c', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'pallet_outdoor', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'pewter_outdoor', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'sevii_outdoor', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'viridian_outdoor', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d4ad4', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d4aec', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d4b04', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d4b1c', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d4b34', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d4b64', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d4b7c', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d5044', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'general__rom_082d505c', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'pallet_outdoor', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'pewter_outdoor', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'sevii_outdoor', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('leafgreen', 'viridian_outdoor', 29, 1, 'b05e2e6b1213093cf15210a3b47f4149d74749e0c0c62cce3201af16711af0b5', 0), ('firered', 'general__rom_082d4af4', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d4b0c', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d4b24', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d4b3c', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d4b54', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d4b84', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d4b9c', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d5064', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d507c', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'pallet_outdoor', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'pewter_outdoor', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'sevii_outdoor', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'viridian_outdoor', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d4ad4', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d4aec', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d4b04', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d4b1c', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d4b34', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d4b64', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d4b7c', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d5044', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'general__rom_082d505c', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'pallet_outdoor', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'pewter_outdoor', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'sevii_outdoor', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('leafgreen', 'viridian_outdoor', 30, 0, '0624aaa4759a6c9404a8e529fc70ee25dc956190cd4a0d538e8958a84b30b84e', 0), ('firered', 'general__rom_082d4af4', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d4b0c', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d4b24', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d4b3c', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d4b54', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d4b84', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d4b9c', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d5064', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d507c', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'pallet_outdoor', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'pewter_outdoor', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'sevii_outdoor', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'viridian_outdoor', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d4ad4', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d4aec', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d4b04', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d4b1c', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d4b34', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d4b64', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d4b7c', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d5044', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'general__rom_082d505c', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'pallet_outdoor', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'pewter_outdoor', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'sevii_outdoor', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('leafgreen', 'viridian_outdoor', 31, 1, '6d23d5140edf5f537b436a7278e2f73a1212ee9f018bc0f63f83b3c3ea01b6fb', 0), ('firered', 'general__rom_082d4af4', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d4b0c', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d4b24', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d4b3c', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d4b54', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d4b84', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d4b9c', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d5064', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d507c', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'pallet_outdoor', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'pewter_outdoor', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'sevii_outdoor', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'viridian_outdoor', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d4ad4', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d4aec', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d4b04', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d4b1c', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d4b34', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d4b64', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d4b7c', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d5044', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'general__rom_082d505c', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'pallet_outdoor', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'pewter_outdoor', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'sevii_outdoor', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('leafgreen', 'viridian_outdoor', 20, 2, '9703d8f7b29f5d2d9cd694415e78d3af7fbc8df9b4c54f76d2ba494cbf54886a', 0), ('firered', 'general__rom_082d4af4', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d4b0c', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d4b24', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d4b3c', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d4b54', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d4b84', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d4b9c', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d5064', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d507c', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'pallet_outdoor', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'pewter_outdoor', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'sevii_outdoor', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'viridian_outdoor', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d4ad4', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d4aec', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d4b04', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d4b1c', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d4b34', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d4b64', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d4b7c', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d5044', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'general__rom_082d505c', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'pallet_outdoor', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'pewter_outdoor', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'sevii_outdoor', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('leafgreen', 'viridian_outdoor', 21, 3, 'e527708edfa00e9ee6817d11833d210441507a0d407f9b11550259163a13731d', 0), ('firered', 'general__rom_082d4af4', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d4b0c', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d4b24', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d4b3c', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d4b54', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d4b84', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d4b9c', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d5064', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d507c', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'pallet_outdoor', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'pewter_outdoor', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'sevii_outdoor', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'viridian_outdoor', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d4ad4', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d4aec', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d4b04', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d4b1c', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d4b34', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d4b64', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d4b7c', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d5044', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'general__rom_082d505c', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'pallet_outdoor', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'pewter_outdoor', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'sevii_outdoor', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('leafgreen', 'viridian_outdoor', 22, 2, '45c02dc20fcfe976687d8ab8ef8dc48750ad641ab73493751c4bba5842b758ae', 0), ('firered', 'general__rom_082d4af4', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d4b0c', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d4b24', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d4b3c', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d4b54', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d4b84', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d4b9c', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d5064', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d507c', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'pallet_outdoor', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'pewter_outdoor', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'sevii_outdoor', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'viridian_outdoor', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d4ad4', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d4aec', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d4b04', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d4b1c', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d4b34', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d4b64', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d4b7c', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d5044', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'general__rom_082d505c', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'pallet_outdoor', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'pewter_outdoor', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'sevii_outdoor', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('leafgreen', 'viridian_outdoor', 23, 3, '09c5c3b1e5aa131d3d19d1ef6a1ac221378b48e1f2e3386e931d31c7121253d7', 0), ('firered', 'general__rom_082d4af4', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d4b0c', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d4b24', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d4b3c', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d4b54', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d4b84', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d4b9c', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d5064', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d507c', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'pallet_outdoor', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'pewter_outdoor', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'sevii_outdoor', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'viridian_outdoor', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d4ad4', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d4aec', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d4b04', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d4b1c', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d4b34', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d4b64', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d4b7c', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d5044', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'general__rom_082d505c', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'pallet_outdoor', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'pewter_outdoor', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'sevii_outdoor', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('leafgreen', 'viridian_outdoor', 36, 2, '17d7b97b6fc659e6f635ae8bed60eb7ae2e05419eef9c8c03763c631669b3114', 0), ('firered', 'general__rom_082d4af4', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d4b0c', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d4b24', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d4b3c', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d4b54', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d4b84', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d4b9c', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d5064', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d507c', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'pallet_outdoor', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'pewter_outdoor', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'sevii_outdoor', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'viridian_outdoor', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d4ad4', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d4aec', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d4b04', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d4b1c', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d4b34', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d4b64', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d4b7c', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d5044', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'general__rom_082d505c', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'pallet_outdoor', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'pewter_outdoor', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'sevii_outdoor', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('leafgreen', 'viridian_outdoor', 37, 3, '9a69d959f7e1af658f5d5083e57310a85bab94f5a781b918ef40c8a27e126ee6', 0), ('firered', 'general__rom_082d4af4', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d4b0c', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d4b24', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d4b3c', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d4b54', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d4b84', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d4b9c', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d5064', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d507c', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'pallet_outdoor', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'pewter_outdoor', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'sevii_outdoor', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'viridian_outdoor', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d4ad4', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d4aec', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d4b04', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d4b1c', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d4b34', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d4b64', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d4b7c', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d5044', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'general__rom_082d505c', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'pallet_outdoor', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'pewter_outdoor', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'sevii_outdoor', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('leafgreen', 'viridian_outdoor', 38, 2, 'ba66a79eddc7563b6f70666e1e8cfe0f6b71e1d50efafb7826dd38e62e8ee7bf', 0), ('firered', 'general__rom_082d4af4', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'general__rom_082d4b0c', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'general__rom_082d4b24', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'general__rom_082d4b3c', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'general__rom_082d4b54', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'general__rom_082d4b84', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'general__rom_082d4b9c', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'general__rom_082d5064', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'general__rom_082d507c', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'pallet_outdoor', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'pewter_outdoor', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'sevii_outdoor', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('firered', 'viridian_outdoor', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d4ad4', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d4aec', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d4b04', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d4b1c', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d4b34', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d4b64', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d4b7c', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d5044', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'general__rom_082d505c', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'pallet_outdoor', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'pewter_outdoor', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'sevii_outdoor', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0), ('leafgreen', 'viridian_outdoor', 39, 3, '972ff2e5aa05d6bd9d4c8ad6b41285b78e4f93a23fe554caf45cb7f864bce224', 0)]

def stable(v):return json.dumps(v,sort_keys=True,separators=(',',':'))
def identity(row):return row['game'],row['style'],row['tileset'],row['id'],row.get('map')
def plain_floor(role):
    return ('floor'in role or role.endswith('tatami_mat'))and not any(w in role for w in('parapet','skylight','foot','head','under','below','border','edge','corner','threshold','door','exit','entrance','puzzle','glyph','altar','shadow'))



def classic_floor_symbol(review,base,direction):
    """New native-size classic symbol; whole GB floor and solid native ink.

    This is a new planar8px counterpart for a known source arrow/stop panel,
    not a claim that Crystal originally contained the Gen3 puzzle panel.
    """
    from reverse_kanto_review import runs
    assert direction in('north','east','south','west','stop')
    arrow=('00011000','00111100','01111110','11111111','00011000','00011000','00011000','00011000')
    points={(x,y)for y,line in enumerate(arrow)for x,bit in enumerate(line)if bit=='1'}
    if direction=='stop':
        points=set()
        for y,(left,right)in enumerate(((3,4),(2,5),(1,6),(0,7),(0,7),(1,6),(2,5),(3,4))):
            points.add((left,y));points.add((right,y))
        points|={(3,3),(4,3),(3,4),(4,4)}
    elif direction=='east':points={(7-y,x)for x,y in points}
    elif direction=='south':points={(7-x,7-y)for x,y in points}
    elif direction=='west':points={(y,7-x)for x,y in points}
    image=review.gb_image(base);ink=review.gb_ref('crystal','UNION_CAVE_1F',0,0)
    assert set(review.gb_image(ink).get_flattened_data())=={(58,58,58,255)},'Solid native GB ink glyph changed'
    darks={};lights={};parts=[]
    luminance=lambda c:2126*c[0]+7152*c[1]+722*c[2]
    for q in range(4):
        palette=set(image.crop((q%2*8,q//2*8,q%2*8+8,q//2*8+8)).get_flattened_data())
        dark=(58,58,58,255)if len(palette)<4 or(58,58,58,255)in palette else min(palette,key=luminance)
        available=palette|{dark};bright=(222,255,222,255)
        light=bright if len(available)<4 or bright in available else max(available,key=luminance)
        assert light!=dark
        darks[q]=dark;lights[q]=light
    for is_glyph,colors in((False,darks),(True,lights)):
        for color in set(colors.values()):
            mask=[(x-4,y-4)in points and colors[y//8*2+x//8]==color if is_glyph else 4<=x<12 and 4<=y<12 and colors[y//8*2+x//8]==color for y in range(16)for x in range(16)]
            ref=copy.deepcopy(ink);ref['palettes']=[[[*color[:3]]for _ in range(4)]for _ in range(8)];ref['monochrome']=False
            for rect in runs(mask):parts.append(dict(donor=ref,srcX=0,srcY=0,**rect))
    assert 0<len(parts)<=32
    art=review.composite(base,parts,'classic_gen2_new_native_size_'+direction+'_floor_symbol');art['overMask']='0'*256
    result=review.render(art)
    for q in range(4):assert len(set(result.crop((q%2*8,q//2*8,q%2*8+8,q//2*8+8)).get_flattened_data()))<=4
    assert all(4<=x<12 and 4<=y<12 or result.getpixel((x,y))==image.getpixel((x,y))for y in range(16)for x in range(16))
    proof=dict(kind='new_classic_floor_symbol',direction=direction,native_symbol_size=[8,8],symbol_origin=[4,4],pixel_scale=1,native_gb_ink=ink,whole_native_floor=base,maximum_colors_per_8px=4,glyph_rows=[''.join('1'if(x,y)in points else'0'for x in range(8))for y in range(8)],contrast_pad=True,all_floor_pixels_outside_8px_symbol_exact=True)
    return art,proof


class Finish(ReverseReview):
    def __init__(self):
        super().__init__('gen2-kanto-finish',GAMES)
        paths=list(dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]",(ROOT/'main.lua').read_text())))
        self.active=[];self.origins={}
        for name in paths:
            if ROOT/name==TARGET:continue
            for index,row in enumerate(preview.read_reviewed(ROOT/name),1):
                self.active.append(row);self.origins[id(row)]=(name,index)
        self.current={identity(r):r for r in self.active if r['game']in GAMES and r['style']=='gen2'}
        self.prior=self.active;self.locations={identity(r):(self.origins[id(r)][0],self.origins[id(r)][1],r)for r in self.current.values()};self.proofs={};self.supersessions={};self.target_module=TARGET
        self.layouts={};self.usage=defaultdict(list);self.maps=[];self.held=[];self.seeds=[];self.missing_borders=[]
        self.source_by_hash=defaultdict(list)
        for game in GAMES:
            for(pair,mid),cell in self.imp.cell_index(game).items():
                self.source_by_hash[cell['pixel_sha256']].append((game,pair,mid))
            for name,spec in sorted(self.imp.table(game,'gba/native/manifest')['layouts'].items()):
                layout=decode_layout(self.cache/game/'data/generated/gba/native'/spec['file'])
                raw=(self.cache/game/'data/generated/gba/native'/spec['file']).read_bytes()
                blob=raw if raw[:4]==b'SVML'else zlib.decompress(raw)
                pw,ph,w,h=struct.unpack_from('<HHHH',blob,6);w=w or pw;h=h or ph
                layout['mids']=[layout['mids'][y*pw+x]for y in range(h)for x in range(w)]
                layout['width'],layout['height']=w,h
                self.layouts[game,name]=(spec,layout)
                for mid in struct.unpack_from('<'+'H'*(blob[14]*blob[15]),blob,16):
                    if(spec['pair'],mid)not in self.imp.cell_index(game):
                        self.missing_borders.append(dict(game=game,map=name,pair=spec['pair'],id=mid,reason='Unavailable native border atlas slot: retain the original black renderer result; no source fingerprint invented.'));continue
                    if not any(v.get('border')and v['map']==name for v in self.usage[game,spec['pair'],mid]):self.usage[game,spec['pair'],mid].append(dict(map=name,count=0,border=True))
                counts=Counter(layout['mids'])
                for mid,n in counts.items():self.usage[game,spec['pair'],mid].append(dict(map=name,count=n))
                covered=sum(n for mid,n in counts.items()if(game,'gen2',spec['pair'],mid,None)in self.current)
                self.maps.append(dict(game=game,map=name,pair=spec['pair'],width=layout['width'],height=layout['height'],
                    cells=len(layout['mids']),covered=covered,remaining=len(layout['mids'])-covered))
        self.source_by_hash={sha:[k for k in keys if k in self.usage]for sha,keys in self.source_by_hash.items()}

    def checked_native(self,pair,mid):
        cell=self.imp.cell_index('firered')[pair,mid]
        signature=catalog.sha(stable(dict(rgba=cell['pixel_sha256'],behavior=cell['behavior'],layers=cell['layer_sha256'])).encode())
        assert MANUAL_SOURCES[pair,mid]==signature,('Previously reviewed manual source art/layers/behavior changed',pair,mid)
        return cell

    def gb_image(self,ref):
        if ref.get('game')=='crystal'and ref.get('monochrome'):
            ts=self.imp.table('crystal','tilesets')[ref['tileset']];sheet=Image.open(self.cache/'crystal'/ts['image']).convert('RGBA')
            block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1));image=preview.native_cell(sheet,ts,block,ref['quadrant'])
            assert catalog.sha(image.tobytes())==ref['hash']and set(image.get_flattened_data())=={(0,0,0,255)}
            return image
        return super().gb_image(ref)

    def inventory(self):
        report=dict(games={g:dict(maps=sum(m['game']==g for m in self.maps),pairs=len({m['pair']for m in self.maps if m['game']==g}),
            source_cells=sum(m['cells']for m in self.maps if m['game']==g),
            used_keys=sum(k[0]==g and any(v['count']for v in u)for k,u in self.usage.items()),border_keys=sum(k[0]==g and any(v.get('border')for v in u)for k,u in self.usage.items()),existing_keys=sum(k[0]==g for k in self.current),
            covered=sum(m['covered']for m in self.maps if m['game']==g))for g in GAMES},maps=self.maps)
        (self.out/'inventory.json').write_text(json.dumps(report,indent=2));return report

    def forward_candidates(self):
        """Proposals require complete16px output equality, then semantic review."""
        groups=defaultdict(list)
        for row in self.active:
            if row['game']!='crystal'or row.get('kind','native')not in('native','native_composite'):continue
            if row.get('asset')or row.get('artOverlay')or row.get('animated'):continue
            refs=([row['donor']]if row.get('donor')else[row['base']]if row.get('base')else[])+[p['donor']for p in row.get('parts',[])]
            if not refs or any(r.get('game')not in('firered','emerald')or r.get('kind')for r in refs):continue
            if not any(r.get('game')=='firered'for r in refs):continue
            pixel=row.get('compositionPixelHash')
            if row.get('donor'):pixel=row['donor']['hash']
            anchors=[r for r in refs if r.get('game')=='firered'and r.get('hash')==pixel]
            if not anchors:continue
            targets=[(g,p,i)for g,p,i in self.source_by_hash.get(pixel,[])if(g,'gen2',p,i,None)not in self.current]
            if targets:
                g,p,i=targets[0];source=preview.native_donor(self.cache,dict(game=g,tileset=p,id=i,hash=pixel),self.packed)
                if not any(px[3]for px in source.get_flattened_data())or all(px[:3]==(0,0,0)for px in source.get_flattened_data()):continue
            if not targets:continue
            name=donor_map(self,row)
            ref=self.gb_ref('crystal',name,row['id'],row['quadrant'])
            assert ref['hash']==row['sourceHash']
            key=pixel,catalog.sha(self.gb_image(ref).tobytes())
            module,index=self.origins[id(row)]
            groups[key].append(dict(row=row,ref=ref,anchor=anchors[0],origin=dict(module=module,index=index),targets=targets))
        by_source=defaultdict(list)
        for key,items in groups.items():by_source[key[0]].append(items)
        candidates=[]
        for pixel,variants in sorted(by_source.items()):
            for items in variants:
                candidate=sorted(items,key=lambda v:(v['row'].get('map')is None,v['ref']['map'],v['row']['role']))[0]
                roles=sorted({i['row']['role']for i in items})
                candidate.update(pixel=pixel,roles=roles,ambiguous=len(variants)>1,
                    unsafe=any(any(word in role for word in UNSAFE)for role in roles))
                candidates.append(candidate)
        # Explicitly reviewed canonical motifs, never an arbitrary conflict winner.
        resolved=[]
        for candidate in candidates:
            roles=candidate['roles'];ref=candidate['ref']
            if all(plain_floor(role)for role in roles):
                native=self.imp.cell_index('crystal')[ref['tileset'],ref['id'],ref['quadrant']]
                if native['collision']==7:candidate['unsafe']=True;candidate['native_floor_role_conflict']='Original GSC glyph is a solid wall/object despite an old generic floor label.'
            if candidate['ambiguous'] and any(r.startswith('freshwater_pond_')for r in roles):
                if ref['map']in('CHERRYGROVE_CITY','ROUTE_30'):
                    candidate['ambiguous']=False;candidate['canonical']='Shared Kanto pond family uses the complete Crystal Johto day bank geometry and palette, rather than the darker Ilex duplicate.'
                else:continue
            if candidate['ambiguous'] and roles==['snowy_cave_floor']:
                if(ref['map'],ref['id'],ref['quadrant'])!=('ICE_PATH_1F',4,3):continue
                candidate['ambiguous']=False;candidate['canonical']='Ice Path complete plain snow floor canonical motif; patterned variants of the same snow material are intentionally unified.'
            resolved.append(candidate)
        candidates=resolved
        # Ordinary material/palette alternatives are routine canonical choices,
        # not questions. Every option here is an explicitly reviewed pure floor.
        floor_groups=defaultdict(list)
        for c in candidates:floor_groups[c['pixel']].append(c)
        discard=set();preferred=('FAST_SHIP_1F','FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN','PLAYERS_HOUSE_1F','GUIDE_GENTS_HOUSE','AZALEA_POKECENTER_1F','CHERRYGROVE_MART','CELADON_DEPT_STORE_1F','SILPH_CO_1F','FIGHTING_DOJO','SAFFRON_GYM','BRUNOS_ROOM','UNION_CAVE_1F','MOUNT_MOON')
        for pixel,options in floor_groups.items():
            if len(options)<2 or not all(all(plain_floor(r)for r in c['roles'])for c in options):continue
            def rank(c):
                name=c['ref']['map'];context=preferred.index(name)if name in preferred else len(preferred)
                return context,name,c['ref']['id'],c['ref']['quadrant']
            eligible=[c for c in options if not c['unsafe']]
            if not eligible:continue
            chosen=min(eligible,key=rank);chosen['ambiguous']=False
            chosen['canonical']='A coherent native Crystal '+chosen['ref']['map']+' ordinary floor motif/palette is selected for this one shared native source material; alternate pure floor motifs are routine variations.'
            discard.update(id(c)for c in options if c is not chosen)
        candidates=[c for c in candidates if id(c)not in discard]
        self.candidates=candidates
        (self.out/'candidate-inventory.json').write_text(json.dumps([dict(number=i,pixel=c['pixel'],roles=c['roles'],
            donor=c['ref'],targets=c['targets'],ambiguous=c['ambiguous'],unsafe=c['unsafe'],origin=c['origin'])for i,c in enumerate(candidates)],indent=2))
        return candidates

    def stage(self):
        for c in self.candidates:
            if c['ambiguous']or c['unsafe']:
                self.held.append(dict(reason='Conflicting Crystal motifs/palettes'if c['ambiguous']else'Whole-object/footprint review required',
                    source_hash=c['pixel'],roles=c['roles'],donor=c['ref'],targets=c['targets']));continue
            role=c['row']['role'];material=any(word in role for word in('floor','ground','water','pond','coast','turf','snow','ice','rock_','wall'))
            anchor=dict(c['anchor'],material=material)
            for game,pair,mid in aliases(self,anchor):
                if(game,pair,mid)not in self.usage or(game,'gen2',pair,mid,None)in self.current:continue
                src=self.imp.cell_index(game)[pair,mid]
                over=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=src['pixel_sha256']),self.packed,
                    ['over'],{'over':src['layer_sha256']['over']})
                opaque=sum(p[3]>0 for p in over.get_flattened_data())
                if opaque not in(0,256):
                    self.held.append(dict(reason='Partial native overhead requires a whole counterpart silhouette',game=game,pair=pair,id=mid,roles=c['roles'],donor=c['ref']));continue
                art=self.native(c['ref'],'classic_gen2_fr_'+role)
                art['overMask']=('1'if opaque else'0')*256
                row=self.row(game,pair,mid,'gen2',art,
                    'Explicit approved Crystal/Gen3 semantic provenance: '+role+'. The complete forward composition equals this entire native16x16 source cell; the original complete Crystal quadrant is retained at1:1. No source IDs are treated as equivalent without identical full RGBA, native layers, behavior and reviewed native context/walkability aliases. Whole-building footprint changes, conflicting original motifs and partial overhead silhouettes are held separately. Source maps, collision, encounters, warps, NPCs, scripts and interactions remain native.')
                row['reverseGen2KantoReview']=dict(kind='exact_complete_forward_cell',pixel_scale=1,
                    approved_forward=c['origin'],approved_role=role,complete_forward_rgba_sha256=c['pixel'],
                    original_crystal_rgba_sha256=catalog.sha(self.gb_image(c['ref']).tobytes()),native_over_pixels=opaque)
                self.seeds.append(dict(game=game,pair=pair,id=mid,role=role,origin=c['origin']))
        self.black_canvases()
        self.whole_buildings()
        self.gym_building()
        self.interior_objects()
        self.clinic_counter()
        self.home_table_and_rug()
        self.cliff_modules()
        self.paved_paths_and_fences()
        self.forest_trees()
        self.safari_trees()
        self.verified_park_tree_upgrades()
        self.tree_collision_review()
        self.clear_material_extensions()
        self.materials()
        self.small_decorative_trees()
        self.ordinary_caves()
        self.ice_cave_family()
        self.reviewed_room_materials()
        self.spin_floor_symbols()
        self.cave_ladders()
        self.cave_ladder_heads()
        self.sandy_shores()
        self.water_rocks()
        self.pure_water()
        self.whole_building_matches()
        native_animations(self)
        self.coherent_water_policy()
        self.native_floor_donor_audit()
        (self.out/'uncertain-queue.json').write_text(json.dumps(self.held,indent=2))
        (self.out/'selected-provenance.json').write_text(json.dumps(self.seeds,indent=2))
        replacement=json.loads((self.out/'exact-old-row-supersessions.json').read_text())
        for entry in self.supersessions.values():
            replacement.append(dict(oldmodule=str(entry['module']),oldindex=entry['old_index'],oldrow=entry['old_row'],oldrow_sha256=entry['full_row_sha256'],newmodule='mappings/reverse_gen2_kanto_finish.lua',newrow=entry['new_row']))
        indices={identity(r):i for i,r in enumerate(self.rows.values(),1)}
        for item in replacement:
            key=identity(item['oldrow']);item['newindex']=indices[key];item['newrow']=copy.deepcopy(self.rows[key])
        (self.out/'exact-old-row-supersessions.json').write_text(json.dumps(replacement,indent=2))
        return list(self.rows.values())

    def black_canvases(self):
        black=None;digest=catalog.sha(Image.new('RGBA',(16,16),(0,0,0,255)).tobytes())
        for name in('FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN','TEAM_ROCKET_BASE_B1F','GOLDENROD_UNDERGROUND'):
            m=self.imp.table('crystal','maps')[name]
            for y in range(m['height']*2):
                for x in range(m['width']*2):
                    ref=self.gb_at('crystal',name,x,y)
                    if ref['hash']==digest:
                        black=ref;black['monochrome']=True
                        black['palettes']=[[[255,255,255],[170,170,170],[85,85,85],[0,0,0]]for _ in range(8)];break
                if black:break
            if black:break
        assert black
        self._black_ref=copy.deepcopy(black)
        hashes={digest,catalog.sha(Image.new('RGBA',(16,16),(0,0,0,0)).tobytes())};rows=[]
        for(game,pair,mid),usage in self.usage.items():
            key=game,'gen2',pair,mid,None
            if key in self.current or key in self.rows:continue
            src=self.imp.cell_index(game)[pair,mid]
            if src['pixel_sha256']not in hashes:continue
            art=self.native(black,'classic_gen2_exact_native_black_canvas');art['overMask']='0'*256
            row=self.row(game,pair,mid,'gen2',art,
                'Exact native black canvas preservation. Both the whole native source and this actual native Crystal neutral glyph are black16x16, checked pixel for pixel. Only this verified all-black glyph uses its neutral palette, avoiding a58-gray DAY tint. No room wall/ceiling/prop or functional image is inferred from a blank source. Original camera borders, concealed tiles, maps, collision, events and source behavior remain unchanged.')
            row['reverseGen2KantoReview']=dict(kind='exact_black_canvas',pixel_scale=1,source_rgba_sha256=src['pixel_sha256'],usage=usage)
            rows.append(dict(game=game,pair=pair,id=mid,usage=usage))
        (self.out/'black-canvas-preservation.json').write_text(json.dumps(dict(exact_native_black=rows,unavailable_native_border_slots=self.missing_borders),indent=2))

    def whole_buildings(self):
        # All dimensions and entrance offsets are taken from the actual complete
        # FireRed Viridian buildings; aliases still require exact source layers.
        self.building_models={}
        source_pair=self.layouts['firered','FR_VIRIDIAN_CITY'][0]['pair']
        native_layouts={
            'home':((680,681,682,683,684),(648,649,650,651,652),(656,657,658,659,660),(669,665,677,678,679)),
            'mart':((40,41,42,43),(48,49,50,51),(56,57,58,59),(64,65,98,99)),
            'center':((688,689,690,691,692),(72,73,74,75,391),(80,81,82,83,399),(88,89,90,91,407),(96,97,98,390,415))}
        definitions={'home':('NEW_BARK_TOWN',12,2),'mart':('CHERRYGROVE_CITY',22,0),'center':('CHERRYGROVE_CITY',28,0)}
        ground=ground_ref(self,'gen2');recipes={};conflicts=[];assemblies=[]
        for kind,layout in native_layouts.items():
            name,ox,oy=definitions[kind];w,h=len(layout[0]),len(layout)
            def rect(sx,sy,ww,hh,dx=0,dy=0):return self.gb_rect('crystal',name,ox*16+sx,oy*16+sy,ww,hh,dx,dy)
            pieces={};whole=Image.new('RGBA',(w*16,h*16))
            for y,ids in enumerate(layout):
                for x,mid in enumerate(ids):
                    if kind=='center':
                        # Keep the whole64px original facade, inserting one
                        # plain brick column before the door. Only flat roof
                        # shingles repeat vertically to retain80px source height.
                        sx=(0,1,1,2,3)[x]*16
                        if y<3:parts=rect(sx,0 if y==0 else 8 if y==1 else 16,16,16)
                        elif x!=1:parts=rect(sx,(y-1)*16,16,16)
                        else:
                            parts=rect(32,32,16,16)
                            if y==4:parts+=rect(8,60,8,4,0,12)+rect(8,60,8,4,8,12)
                    elif kind=='home':
                        if y<2:parts=rect((0,1,1,2,3)[x]*16,y*16,16,16)
                        elif x!=2:parts=rect((0,1,1,2,3)[x]*16,y*16,16,16)
                        else:parts=rect(8,y*16,8,16)+rect(8,y*16,8,16,8,0)
                    else:
                        if y<2:parts=rect(x*16,y*16,16,16)
                        else:
                            # Native brick field and the original outer caps.
                            parts=rect(32,32,16,16)
                            if y==3:
                                parts+=rect(8,60,8,4,0,12)+rect(8,60,8,4,8,12)
                            # Preserve the complete entrance24px high at the
                            # actual FR/LG x2 doorway, and complete MART lettering.
                            if x==2:parts+=rect(16,40 if y==2 else 48,16,8 if y==2 else 16,0,8 if y==2 else 0)
                            if y==2 and x in(0,1):
                                parts+=rect(32 if x==0 else 44,48,12 if x==0 else 16,16,4 if x==0 else 0,0)
                            # Original left display/window stays complete.
                            if y==3 and x==0:parts+=rect(4,56,12,8,4,8)
                            if x==0:parts+=rect(0,y*16,4,16)
                            if x==3:parts+=rect(60,y*16,4,16,12,0)
                    art=self.composite(None,parts,'classic_gen2_complete_'+kind)
                    pieces[x,y]=art;whole.paste(self.render(art),(x*16,y*16))
            outside=exterior(whole,set(self.gb_image(ground).get_flattened_data())|{(222,255,222,255)})
            original=Image.new('RGBA',(64,64))
            for yy in range(4):
                for xx in range(4):original.paste(self.gb_image(self.gb_at('crystal',name,ox+xx,oy+yy)),(xx*16,yy*16))
            pixel_checks=0
            if kind in('home','center'):
                for yy in range(64):
                    for xx in range(64):
                        col=xx//16
                        dx=((0,1,3,4)[col]if kind=='home'else(0,2,3,4)[col])*16+xx%16
                        dy=yy if kind=='home'or yy<16 else yy+16
                        assert whole.getpixel((dx,dy))==original.getpixel((xx,yy)),(kind,xx,yy)
                        pixel_checks+=1
            else:
                for sx,sy,ww,hh,dx,dy in((0,0,64,32,0,0),(16,40,16,24,32,40),(32,48,28,16,4,32),(4,56,12,8,4,56),(60,32,4,32,60,32)):
                    for yy in range(hh):
                        for xx in range(ww):assert whole.getpixel((dx+xx,dy+yy))==original.getpixel((sx+xx,sy+yy)),(kind,sx+xx,sy+yy)
                    pixel_checks+=ww*hh
            whole.save(self.out/('whole-'+kind+'-crystal.png'))
            native=Image.new('RGBA',(w*16,h*16))
            for y,ids in enumerate(layout):
                for x,mid in enumerate(ids):
                    src=self.checked_native(source_pair,mid)
                    seed=dict(game='firered',tileset=source_pair,id=mid,hash=src['pixel_sha256'])
                    native.paste(preview.native_donor(self.cache,seed,self.packed),(x*16,y*16))
                    mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
                    art=self.composite(ground,clip_parts(pieces[x,y]['parts'],mask),'classic_gen2_whole_'+kind+'_native_modules')
                    over=preview.native_donor(self.cache,seed,self.packed,['over'],{'over':src['layer_sha256']['over']})
                    art['overMask']=''.join('1'if bit and any(p[3]for p in over.get_flattened_data())else'0'for bit in mask)
                    key=source_pair,mid
                    if key in recipes and(self.render(recipes[key]).tobytes()!=self.render(art).tobytes()or recipes[key]['overMask']!=art['overMask']):
                        conflicts.append(dict(pair=source_pair,id=mid,kinds=[recipes[key]['role'],kind]));continue
                    recipes[key]=art
            native.save(self.out/('whole-'+kind+'-firered.png'))
            panel=Image.new('RGB',(w*16*8+24,h*16*4+28),'#18212b');panel.paste(native.resize((w*64,h*64),Image.Resampling.NEAREST),(4,24));panel.paste(whole.resize((w*64,h*64),Image.Resampling.NEAREST),(w*64+16,24));panel.save(self.out/('whole-'+kind+'-comparison.png'))
            assemblies.append(dict(kind=kind,source_map='FR_VIRIDIAN_CITY',source_pair=source_pair,layout=layout,dimensions=[w*16,h*16],native_scale=1,original_crystal_pixels_checked=pixel_checks))
        assert not conflicts,conflicts
        for kind,layout in native_layouts.items():
            self.building_models[kind]=dict(pair=source_pair,layout=layout,entrance={'home':(1,3),'mart':(2,3),'center':(2,4)}[kind],recipes={mid:copy.deepcopy(recipes[source_pair,mid])for ids in layout for mid in ids})
        for(pair,mid),art in recipes.items():
            for game,target_pair,target_mid in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',target_pair,target_mid,None
                if(game,target_pair,target_mid)not in self.usage or key in self.current:continue
                # Explicit complete-building assembly takes precedence over an
                # incomplete forward fragment generated earlier in this tool.
                self.rows.pop(key,None)
                row=self.row(game,target_pair,target_mid,'gen2',art,
                    'Explicit complete native building assembly reviewed against the entire FireRed Viridian home/Mart/Center footprint and entrance. Original Crystal roof caps, brickwork, complete doorway/frame, windows and service lettering retain native1:1 pixels. Only plain roof/brick modules repeat to fill the native source envelope; doorway matches the original source exit. Whole-building outside flood exposes classic ground at true corners, and opaque counterpart pixels keep original overhead priority. Source maps/collision/warps/NPCs/scripts unchanged. No map-specific GBA atlas scope.')
                row['reverseGen2KantoReview']=dict(kind='complete_native_building_modules',pixel_scale=1,source_pair=pair,source_id=mid,whole_assembly=art['role'])
        (self.out/'whole-building-evidence.json').write_text(json.dumps(dict(assemblies=assemblies,conflicts=conflicts),indent=2))

    def gym_building(self):
        from reverse_kanto_review import runs
        layout=((321,322,322,322,322,323),(329,330,330,330,330,331),(336,337,338,339,340,342),(344,345,346,347,348,350));pair='viridian_outdoor'
        definition=self.imp.table('crystal','maps')['VIRIDIAN_CITY']
        assert any(w.get('destMap')=='VIRIDIAN_GYM'and(w['x'],w['y'])==(32,7)for w in definition['warps'])
        spec,native_map=self.layouts['firered','FR_VIRIDIAN_CITY'];assert spec['pair']==pair
        assert all(native_map['mids'][(7+y)*native_map['width']+33+x]==mid for y,ids in enumerate(layout)for x,mid in enumerate(ids))
        original=Image.new('RGBA',(96,64));whole=original.copy();source=original.copy();recipes={};pieces={}
        for y in range(4):
            for x in range(6):original.paste(self.gb_image(self.gb_at('crystal','VIRIDIAN_CITY',28+x,4+y)),(x*16,y*16))
        assert original.crop((16,48,32,64)).tobytes()==original.crop((32,48,48,64)).tobytes(),'Gym removable middle window module is not a true repeat'
        for y,ids in enumerate(layout):
            for x,mid in enumerate(ids):
                if y<3:parts=self.gb_rect('crystal','VIRIDIAN_CITY',(28+x)*16,(4+y)*16,16,16)
                elif x<3:parts=self.gb_rect('crystal','VIRIDIAN_CITY',(28+(0,1,3)[x])*16,7*16,16,16)
                elif x==3:parts=self.gb_rect('crystal','VIRIDIAN_CITY',32*16,7*16,16,16)
                else:
                    # One original8px right window pane repeats three times,
                    # between both complete4px outer frames. No pane is split.
                    parts=[];left=64+(x-4)*16;right=left+16
                    for dx,sx,ww in((64,80,4),(68,84,8),(76,84,8),(84,84,8),(92,92,4)):
                        a=max(left,dx);b=min(right,dx+ww)
                        if b>a:parts+=self.gb_rect('crystal','VIRIDIAN_CITY',28*16+sx+a-dx,7*16,b-a,16,a-left,0)
                art=self.composite(None,parts,'classic_gen2_complete_kanto_gym');pieces[x,y]=art;whole.paste(self.render(art),(x*16,y*16))
                src=self.checked_native(pair,mid);source.paste(preview.native_donor(self.cache,dict(game='firered',tileset=pair,id=mid,hash=src['pixel_sha256']),self.packed),(x*16,y*16))
        checks=0
        for yy in range(64):
            for xx in range(96):
                if yy<48:dx=xx
                elif xx<32:dx=xx
                elif xx<48:dx=xx-16
                elif xx<80:dx=xx-16
                elif xx<84:dx=xx-16
                elif xx<92:dx=xx-16
                else:dx=xx
                assert whole.getpixel((dx,yy))==original.getpixel((xx,yy)),('Gym unique source pixel lost',xx,yy,dx);checks+=1
        ground=ground_ref(self,'gen2');outside=exterior(whole,set(self.gb_image(ground).get_flattened_data())|{(222,255,222,255)})
        for y,ids in enumerate(layout):
            for x,mid in enumerate(ids):
                mask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
                art=self.composite(ground,clip_parts(pieces[x,y]['parts'],mask),'classic_gen2_complete_kanto_gym')
                src=self.checked_native(pair,mid);over=preview.native_donor(self.cache,dict(game='firered',tileset=pair,id=mid,hash=src['pixel_sha256']),self.packed,['over'],{'over':src['layer_sha256']['over']})
                art['overMask']=''.join('1'if bit and any(p[3]for p in over.get_flattened_data())else'0'for bit in mask)
                if mid in recipes:assert self.render(recipes[mid]).tobytes()==self.render(art).tobytes()and recipes[mid]['overMask']==art['overMask'],('Repeated native Gym module differs',mid)
                recipes[mid]=art
        self.building_models['gym']=dict(pair=pair,layout=layout,entrance=(3,3),recipes=copy.deepcopy(recipes))
        for mid,art in recipes.items():
            for game,target,alias in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',target,alias,None
                if(game,target,alias)not in self.usage or key in self.current:continue
                self.rows.pop(key,None)
                row=self.row(game,target,alias,'gen2',art,
                    'Complete actual Crystal Viridian Gym counterpart,96x64 at native1:1 pixels, reviewed against the whole FireRed Viridian Gym. The original source entrance is relative4,3; the native FireRed entrance is3,3. Complete doorway moves one cell left; one truly identical whole window module is moved from the left bank to the right, where the complete8px native pane repeats between both complete outer frames. Every original unique roof, GYM letter, window pane, frame and door pixel is checked intact. Whole-building exterior exposes correct Crystal ground; source overhead ordering follows opaque counterpart art. No source collision, entrance warp, actor, script or map is moved.')
                row['reverseGen2KantoReview']=dict(kind='complete_actual_kanto_gym',pixel_scale=1,source_map='FR_VIRIDIAN_CITY',source_origin=[33,7],native_source_id=mid,original_crystal_map='VIRIDIAN_CITY',original_crystal_origin=[28,4],original_source_pixels_checked=checks)
        source.save(self.out/'whole-gym-firered.png');whole.save(self.out/'whole-gym-crystal.png')
        panel=Image.new('RGB',(792,284),'#18212b');panel.paste(source.resize((384,256),Image.Resampling.NEAREST),(4,24));panel.paste(whole.resize((384,256),Image.Resampling.NEAREST),(400,24));panel.save(self.out/'whole-gym-comparison.png')

    def whole_building_matches(self):
        # Only an exact complete rectangle plus native entrance can authorize
        # a new secondary-pair alias. Cell collisions never identify a house.
        signatures={};native_images={};instances=[];proposals=defaultdict(list)
        ground_pixels=self.gb_image(ground_ref(self,'gen2')).tobytes();known_ground=set()
        for r in list(self.current.values())+list(self.rows.values()):
            if r.get('kind','native')!='native'or not any(word in r['role']for word in('field','lawn','ground','open_path')):continue
            if self.render(r).tobytes()==ground_pixels:known_ground.add(r['sourceHash'])
        def signature(game,pair,mid):
            key=game,pair,mid
            if key not in signatures:
                c=self.imp.cell_index(game)[pair,mid];signatures[key]=(c['pixel_sha256'],c['behavior'],stable(c['layer_sha256']))
            return signatures[key]
        def images(game,pair,mid):
            key=game,pair,mid
            if key not in native_images:
                c=self.imp.cell_index(game)[pair,mid];ref=dict(game=game,tileset=pair,id=mid,hash=c['pixel_sha256'])
                native_images[key]=[preview.native_donor(self.cache,ref,self.packed)]+[preview.native_donor(self.cache,ref,self.packed,[layer],{layer:c['layer_sha256'][layer]})for layer in('under','mid','over')]
            return native_images[key]
        def palette_match(model,game,pair,actual,ox,oy):
            mapping={};inverse={};w=actual['width'];excluded=[];checked=0
            for y,ids in enumerate(model['layout']):
                for x,mid in enumerate(ids):
                    tm=actual['mids'][(oy+y)*w+ox+x]
                    if signature('firered',model['pair'],mid)[1]!=signature(game,pair,tm)[1]:return None
                    lefts,rights=images('firered',model['pair'],mid),images(game,pair,tm)
                    background=catalog.sha(lefts[1].tobytes())in known_ground and catalog.sha(rights[1].tobytes())in known_ground
                    left_mask=[a[3]>0 or b[3]>0 for a,b in zip(lefts[2].get_flattened_data(),lefts[3].get_flattened_data())]
                    excluded_count=0
                    for plane,(left,right)in enumerate(zip(lefts,rights)):
                        for i,(ca,cb)in enumerate(zip(left.get_flattened_data(),right.get_flattened_data())):
                            if background and plane<2 and not left_mask[i]:excluded_count+=1;continue
                            checked+=1
                            if ca[3]!=cb[3]:return None
                            if ca[3]==0:continue
                            if ca in mapping and mapping[ca]!=cb or cb in inverse and inverse[cb]!=ca:return None
                            mapping[ca]=cb;inverse[cb]=ca
                    if excluded_count:excluded.append(dict(x=x,y=y,canonical_under_rgba=catalog.sha(lefts[1].tobytes()),source_under_rgba=catalog.sha(rights[1].tobytes()),pixels=excluded_count,matching_reviewed_classic_ground=True))
            return dict(palette=[dict(source=list(k),target=list(v))for k,v in sorted(mapping.items())],checked=checked,background=excluded)
        for kind,model in self.building_models.items():
            layout=model['layout'];ww,hh=len(layout[0]),len(layout)
            for(game,name),(spec,actual)in self.layouts.items():
                pair=spec['pair'];w,h=actual['width'],actual['height'];warps=self.imp.table(game,'gba/warps').get(name,[])
                expected={'home':('HOUSE','SCHOOL'),'mart':('MART',),'center':('POKEMON_CENTER','POKECENTER'),'gym':('GYM',)}[kind]
                for warp in catalog.lua_array(warps):
                    if not any(v in warp.get('destMap','')for v in expected):continue
                    ox,oy=warp['x']-model['entrance'][0],warp['y']-model['entrance'][1]
                    if ox<0 or oy<0 or ox+ww>w or oy+hh>h:continue
                    palette=palette_match(model,game,pair,actual,ox,oy)
                    if palette is None:continue
                    source_cells=[]
                    for yy in range(hh):
                        for xx in range(ww):
                            mm=actual['mids'][(oy+yy)*w+ox+xx];cc=self.imp.cell_index(game)[pair,mm]
                            source_cells.append(dict(x=xx,y=yy,id=mm,rgba=cc['pixel_sha256'],behavior=cc['behavior'],layers=cc['layer_sha256']))
                    witness=dict(game=game,map=name,pair=pair,origin=[ox,oy],dimensions=[ww,hh],kind=kind,entrance=copy.deepcopy(warp),source_palette_bijection=palette['palette'],separately_reviewed_outside_ground=palette['background'],source_cells=source_cells,whole_source_fingerprint=catalog.sha(stable(source_cells).encode()),all_final_under_mid_over_pixels_checked=palette['checked'],keys=[])
                    for y in range(hh):
                        for x in range(ww):
                            tm=actual['mids'][(oy+y)*w+ox+x];key=(game,'gen2',pair,tm,None);source_mid=layout[y][x];art=model['recipes'][source_mid]
                            witness['keys'].append(key);proposals[key].append((art,witness,source_mid))
                    instances.append(witness)
        conflicting=set();mismatched=[]
        for key,options in proposals.items():
            images={(catalog.sha(self.render(v[0]).tobytes()),v[0]['overMask'])for v in options}
            if len(images)>1:conflicting.add(key)
            old=self.current.get(key)
            if old and(catalog.sha(self.render(old).tobytes()),old.get('overMask','0'*256))not in images:conflicting.add(key)
        rejected={id(v)for v in instances if any(tuple(k)in conflicting for k in v['keys'])}
        applied=[]
        for key,options in proposals.items():
            safe=[v for v in options if id(v[1])not in rejected]
            if not safe or key in self.current:continue
            art,witness,source_mid=safe[0];game,style,pair,mid,_=key;self.rows.pop(key,None)
            row=self.row(game,pair,mid,style,art,
                'Exact complete native building footprint match, independently checked across every roof/wall/window/door cell using either exact RGBA or one complete injective palette substitution jointly across every final/under/mid/over pixel, with exact alpha geometry and behavior against the reviewed complete Viridian assembly. A native entrance warp at the same relative door anchor and matching home/Mart/Center/Gym purpose is mandatory. This approves complete source-building aliases across secondary pairs, never isolated collision or single-door matches. Every source palette/shape comparison is recorded across the whole object; no independently normalized cell is enough. Only outside UNDER ground may differ when its entire16px image independently equals a separately reviewed open-field source whose selected classic ground is identical; all MID/OVER pixels and FINAL/UNDER inside the complete object remain checked. Cliff/other-object backgrounds are excluded. Shared atlas keys must require the same complete Crystal recipe in every approved instance; conflicting instances and preexisting complete mappings are preserved. Native Crystal pixels remain1:1, source maps, warps, collision and actors remain unchanged.')
            row['reverseGen2KantoReview']=dict(kind='exact_complete_building_footprint_alias',pixel_scale=1,canonical_source_pair=self.building_models[witness['kind']]['pair'],canonical_source_id=source_mid,whole_footprints=[{k:v for k,v in o[1].items()if k not in('keys','source_cells')}for o in safe])
            applied.append(dict(game=game,pair=pair,id=mid,witnesses=len(safe)))
        for v in instances:
            if id(v)in rejected:mismatched.append({k:value for k,value in v.items()if k!='keys'})
        (self.out/'whole-building-alias-evidence.json').write_text(json.dumps(dict(complete_instances=len(instances),instances=[{k:v for k,v in instance.items()if k!='keys'}for instance in instances],applied=applied,held_conflicting_instances=mismatched,conflicting_keys=list(conflicting)),indent=2))

    def interior_objects(self):
        from reverse_kanto_review import runs
        pair=self.layouts['firered','FR_OAKS_LAB'][0]['pair']
        # Source opaque art is14..45 inside the48px shelf canvas and3..29
        # inside the32px table canvas. Keep their actual native ground anchors.
        cases={
            'lab_bookcases':dict(layout=((107,108),(115,116),(643,644)),origin=(6,0),donor_size=(16,32),top=14,rows=list(range(32)),repeat_columns=True),
            'lab_research_table':dict(layout=((680,681,682),(688,689,690)),origin=(6,3),donor_size=(48,32),top=3,rows=list(range(8))+[4,5,6]+list(range(8,24)),repeat_columns=False)}
        evidence=[];floor=self.gb_ref('crystal','ELMS_LAB',1,0);wall=self.gb_ref('crystal','ELMS_LAB',8,0)
        for kind,cfg in cases.items():
            layout=cfg['layout'];width,height=len(layout[0]),len(layout);dw,dh=cfg['donor_size'];ox,oy=cfg['origin'];top=cfg['top'];rows=cfg['rows']
            donor=Image.new('RGBA',(dw,dh))
            for y in range(dh//16):
                for x in range(dw//16):donor.paste(self.gb_image(self.gb_at('crystal','ELMS_LAB',ox+x,oy+y)),(x*16,y*16))
            outside=exterior(donor,set(self.gb_image(floor).get_flattened_data()))
            kept={(x,y)for y in range(dh)for x in range(dw)if(x,y)not in outside}
            bbox=[min(x for x,y in kept),min(y for x,y in kept),max(x for x,y in kept)+1,max(y for x,y in kept)+1]
            assert bbox==([0,0,16,32]if cfg['repeat_columns']else[0,0,48,24]),(kind,bbox)
            # Every original opaque native object pixel is retained; only a
            # plain three-row table panel repeats, with complete caps/feet intact.
            assert set(range(bbox[1],bbox[3]))<=set(rows)
            whole=Image.new('RGBA',(width*16,height*16));source=whole.copy();native_pixels=0
            for y,ids in enumerate(layout):
                for x,mid in enumerate(ids):
                    base=wall if cfg['repeat_columns']and y==0 else floor;parts=[];mask=[]
                    for yy in range(16):
                        gy=y*16+yy;sy=rows[gy-top]if top<=gy<top+len(rows)else None
                        bits=[]
                        for xx in range(16):
                            sx=xx if cfg['repeat_columns']else x*16+xx
                            bits.append(sy is not None and(sx,sy)in kept)
                        mask+=bits
                        for span in runs(bits+[False]*240):
                            # runs receives one16px row only; transfer its true
                            # source and destination y without any image scaling.
                            parts+=self.gb_rect('crystal','ELMS_LAB',ox*16+(span['x']if cfg['repeat_columns']else x*16+span['x']),oy*16+sy,span['w'],1,span['x'],yy)
                    assert len(parts)<=32,(kind,x,y,len(parts))
                    art=self.composite(base,parts,'classic_gen2_complete_'+kind);whole.paste(self.render(art),(x*16,y*16))
                    native=self.checked_native(pair,mid)
                    source.paste(preview.native_donor(self.cache,dict(game='firered',tileset=pair,id=mid,hash=native['pixel_sha256']),self.packed),(x*16,y*16))
                    for game,target,alias in aliases(self,dict(tileset=pair,id=mid)):
                        key=game,'gen2',target,alias,None
                        if(game,target,alias)not in self.usage or key in self.current:continue
                        src=self.imp.cell_index(game)[target,alias]
                        over=preview.native_donor(self.cache,dict(game=game,tileset=target,id=alias,hash=src['pixel_sha256']),self.packed,['over'],{'over':src['layer_sha256']['over']})
                        art['overMask']=''.join('1'if bit and any(p[3]for p in over.get_flattened_data())else'0'for bit in mask)
                        self.rows.pop(key,None)
                        row=self.row(game,target,alias,'gen2',art,
                            'Actual complete Oak laboratory '+kind+' assembly, reviewed across its whole native canvas and opaque ground anchor. Complete original Crystal Elm laboratory furniture retains every original opaque object pixel at1:1. Native16x32 cabinet columns repeat side by side inside the32x48 source canvas, anchored at nativey46; no extra book rows enlarge or lower the cabinet. The whole48px table retains caps, frame and feet; only one plain three-row table panel repeats to fill the original27px art height, retaining nativey30 ground anchor. Outside source floor is masked as one whole object and rebuilt using the correct native Crystal lab floor/wall. Original collision, NPCs, interactions, scripts and maps unchanged.')
                        row['reverseGen2KantoReview']=dict(kind='complete_native_interior_assembly',pixel_scale=1,source_pair=pair,source_id=mid,assembly=kind,source_object_bbox=bbox,target_top=top,target_rows=rows)
                    native_pixels+=sum(mask)
            retained_checks=0
            for xx,yy in kept:
                for col in(range(width)if cfg['repeat_columns']else(0,)):
                    dx=col*16+xx if cfg['repeat_columns']else xx;dy=top+rows.index(yy)
                    assert whole.getpixel((dx,dy))==donor.getpixel((xx,yy)),(kind,xx,yy,dx,dy)
                    retained_checks+=1
            whole.save(self.out/(kind+'-crystal.png'));source.save(self.out/(kind+'-firered.png'))
            panel=Image.new('RGB',(width*16*8+24,height*64+28),'#18212b');panel.paste(source.resize((width*64,height*64),Image.Resampling.NEAREST),(4,24));panel.paste(whole.resize((width*64,height*64),Image.Resampling.NEAREST),(width*64+16,24));panel.save(self.out/(kind+'-comparison.png'))
            evidence.append(dict(kind=kind,source_map='FR_OAKS_LAB',source_pair=pair,layout=layout,canvas_dimensions=[width*16,height*16],source_object_bbox=bbox,target_top=top,target_rows=rows,native_scale=1,all_original_opaque_pixels_retained=True,retained_object_pixels=len(kept),target_object_pixels=native_pixels,original_opaque_pixels_checked=retained_checks))
        (self.out/'whole-interior-evidence.json').write_text(json.dumps(evidence,indent=2))

    def home_table_and_rug(self):
        from reverse_kanto_review import runs
        layout=((67,68,68,68,68,70),(83,75,76,77,78,86),(83,75,84,85,78,86),(91,92,92,92,92,94));pair='player_house'
        source=Image.new('RGBA',(96,64));native_floor=self.checked_native(pair,1)
        floor_image=preview.native_donor(self.cache,dict(game='firered',tileset=pair,id=1,hash=native_floor['pixel_sha256']),self.packed)
        for y,ids in enumerate(layout):
            for x,mid in enumerate(ids):
                src=self.checked_native(pair,mid);source.paste(preview.native_donor(self.cache,dict(game='firered',tileset=pair,id=mid,hash=src['pixel_sha256']),self.packed),(x*16,y*16))
        outside=exterior(source,set(floor_image.get_flattened_data()))
        carpet=self.gb_ref('crystal','GUIDE_GENTS_HOUSE',15,0);floor=self.gb_ref('crystal','PLAYERS_HOUSE_1F',3,0)
        table=Image.new('RGBA',(32,32))
        for y in range(2):
            for x in range(2):table.paste(self.gb_image(self.gb_at('crystal','GUIDE_GENTS_HOUSE',3+x,3+y)),(x*16,y*16))
        table_out=exterior(table,set(self.gb_image(carpet).get_flattened_data()))
        stool=self.gb_at('crystal','GUIDE_GENTS_HOUSE',2,3);stool_out=exterior(self.gb_image(stool),set(self.gb_image(carpet).get_flattened_data()))
        recipes={};whole=Image.new('RGBA',(96,64))
        for y,ids in enumerate(layout):
            for x,mid in enumerate(ids):
                rugmask=[(x*16+px,y*16+py)not in outside for py in range(16)for px in range(16)]
                parts=[dict(v,donor=carpet,srcX=v['x'],srcY=v['y'])for v in runs(rugmask)]
                if mid in(75,78):
                    mask=[(px,py)not in stool_out for py in range(16)for px in range(16)]
                    parts+=[dict(v,donor=stool,srcX=v['x'],srcY=v['y'])for v in runs(mask)]
                elif mid in(76,77,84,85):
                    tx,ty=(x-2)*16,(y-1)*16;ref=self.gb_at('crystal','GUIDE_GENTS_HOUSE',3+x-2,3+y-1)
                    mask=[(tx+px,ty+py)not in table_out for py in range(16)for px in range(16)]
                    parts+=[dict(v,donor=ref,srcX=v['x'],srcY=v['y'])for v in runs(mask)]
                assert len(parts)<=32,(mid,len(parts))
                art=self.composite(floor,parts,'classic_gen2_complete_house_table_rug_and_stools');art['overMask']='0'*256
                if mid in recipes:assert self.render(recipes[mid]).tobytes()==self.render(art).tobytes(),('Repeated rug module differs',mid)
                recipes[mid]=art;whole.paste(self.render(art),(x*16,y*16))
        for mid,art in recipes.items():
            for game,target,alias in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',target,alias,None
                if(game,target,alias)not in self.usage or key in self.current:continue
                self.rows.pop(key,None)
                row=self.row(game,target,alias,'gen2',art,
                    'Complete native96x64 household table/rug/four-seat assembly, reviewed as one object family in the actual FireRed player house. Complete original Crystal32x32 household table and four native backless seats retain every foreground pixel at1:1; the same original carpet material repeats beneath them. Whole-source exterior floor flood preserves the native rug outline and exposes the selected Crystal wood outside it. No floor is baked behind chairs/table, no frame or stool is scaled/cropped, and no source actor/chair position, collision or interaction is moved.')
                row['reverseGen2KantoReview']=dict(kind='complete_house_table_and_rug_family',pixel_scale=1,source_pair=pair,source_id=mid,whole_source_rgba_sha256=catalog.sha(source.tobytes()))
        foreground_checks=0
        for xx in range(32):
            for yy in range(32):
                if(xx,yy)not in table_out:
                    assert whole.getpixel((32+xx,16+yy))==table.getpixel((xx,yy));foreground_checks+=1
        for dx,dy in((16,16),(64,16),(16,32),(64,32)):
            for xx in range(16):
                for yy in range(16):
                    if(xx,yy)not in stool_out:
                        assert whole.getpixel((dx+xx,dy+yy))==self.gb_image(stool).getpixel((xx,yy));foreground_checks+=1
        source.save(self.out/'home-table-rug-firered.png');whole.save(self.out/'home-table-rug-crystal.png')
        panel=Image.new('RGB',(96*8+24,64*4+28),'#18212b');panel.paste(source.resize((384,256),Image.Resampling.NEAREST),(4,24));panel.paste(whole.resize((384,256),Image.Resampling.NEAREST),(400,24));panel.save(self.out/'home-table-rug-comparison.png')
        (self.out/'home-table-rug-evidence.json').write_text(json.dumps(dict(layout=layout,source_map='FR_PLAYERS_HOUSE_1F',source_origin=[4,3],source_dimensions=[96,64],native_scale=1,whole_source_rgba_sha256=catalog.sha(source.tobytes()),table_foreground_pixels=1024-len(table_out),native_stool_foreground_pixels=256-len(stool_out),original_foreground_pixels_checked=foreground_checks),indent=2))

    def clinic_counter(self):
        # Native counter front is seven cells wide; its four identical plain
        # modules must produce one consistent counterpart in the global atlas.
        # All three native Crystal ball holders and the complete right terminal
        # remain intact, with plain counter spans repeated between them.
        approved={697:(4,2),700:(0,2),664:(2,2),701:(5,2),685:(5,0),693:(5,1)}
        for mid,(x,y)in approved.items():
            self.checked_native('network',mid)
            ref=self.gb_at('crystal','AZALEA_POKECENTER_1F',x,y)
            art=self.native(ref,'classic_gen2_complete_clinic_counter_'+str(mid))
            if mid==685:
                from reverse_kanto_review import runs
                wall=self.gb_at('crystal','AZALEA_POKECENTER_1F',3,0);floor=self.gb_at('crystal','AZALEA_POKECENTER_1F',3,1)
                assert ref['hash']=='48b41d345afb5cb606795b83cc7bf6f0ba6048a76b38fd21d48bb498a22d591b'
                assert wall['hash']=='b6513484fa718548620f6463a1d48517fcf90bc13cb93199f61b474cd99fd49b'
                bounds=CLINIC_POST_UPPER_BOUNDS;mask=[left<=xx<=right for yy,(left,right)in enumerate(bounds)for xx in range(16)]
                original,wall_pixels=self.gb_image(ref),self.gb_image(wall)
                assert all(mask[yy*16+xx]or original.getpixel((xx,yy))==wall_pixels.getpixel((xx,yy))for yy in range(16)for xx in range(16))
                pieces=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)]
                art=self.composite(floor,pieces,'classic_gen2_complete_clinic_counter_'+str(mid));result=self.render(art)
                assert all(not mask[yy*16+xx]or result.getpixel((xx,yy))==original.getpixel((xx,yy))for yy in range(16)for xx in range(16))
            art['overMask']='0'*256
            for game,pair,target in aliases(self,dict(tileset='network',id=mid)):
                key=game,'gen2',pair,target,None
                if(game,pair,target)not in self.usage or key in self.current:continue
                self.rows.pop(key,None)
                row=self.row(game,pair,target,'gen2',art,
                    'Actual complete native FR/LG clinic counter family: seven-cell front [697,700,700,664,700,700,701] and its full three-cell right terminal. The original Crystal counter end, all three ball-holder details and the complete right pole/terminal across its three-cell48px source span are retained at1:1; only the upper cell original identical old gray wallpaper is replaced with the exact selected staff floor around the intact post; plain counter modules repeat only where the native source atlas repeats them. No flower is mistaken for a standalone terminal: this is the complete corresponding clinic counter architecture. Native standing positions, interactions, nurse/player collision, maps and scripts remain unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_native_clinic_counter_family',pixel_scale=1,source_pair='network',source_id=mid,original_crystal_cell=[x,y])

    def cliff_modules(self):
        # These are the exact complete Kanto cliff/raised-earth counterparts
        # reviewed in gen2_kanto_shores_finish, viewed as one coherent family.
        inventory=[]
        for mid,(name,b,q,origin)in CLIFF_MODULES.items():
            ref=self.gb_ref('crystal',name,b,q)
            approved=preview.read_reviewed(ROOT/origin[0])[origin[1]-1]
            assert approved['game']=='crystal'and approved['id']==b and approved['quadrant']==q and approved['sourceHash']==ref['hash']
            assert approved['role']=='kanto_complete_native_raised_earth_'+str(mid)
            refs=([approved['donor']]if approved.get('donor')else[approved['base']]if approved.get('base')else[])+[p['donor']for p in approved.get('parts',[])]
            anchors=[r for r in refs if r.get('game')=='firered'and r.get('id')==mid];assert anchors,(mid,refs)
            signatures=set()
            for anchor in anchors:
                native=self.imp.cell_index('firered')[anchor['tileset'],mid]
                assert native['pixel_sha256']==anchor['hash']
                signatures.add((native['pixel_sha256'],native['behavior'],stable(native['layer_sha256'])))
            for(game,pair,target),usage in self.usage.items():
                key=game,'gen2',pair,target,None
                if key in self.current:continue
                src=self.imp.cell_index(game)[pair,target]
                if(src['pixel_sha256'],src['behavior'],stable(src['layer_sha256']))not in signatures:continue
                over=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=target,hash=src['pixel_sha256']),self.packed,['over'],{'over':src['layer_sha256']['over']})
                assert not any(p[3]for p in over.get_flattened_data()),(pair,target)
                art=self.native(ref,'classic_gen2_complete_kanto_cliff_'+str(mid));art['overMask']='0'*256
                self.rows.pop(key,None)
                row=self.row(game,pair,target,'gen2',art,
                    'Explicit whole-family native Kanto raised-earth/cliff review: source directional module'+str(mid)+'. The complete corresponding original Crystal16px cliff quadrant was previously reviewed against this exact native FireRed directional cliff, including its original uphill/downhill/inward corner geometry. The family is now selected coherently in the actual Kanto day context. Entire native Crystal quadrant remains1:1, without mirroring, cropping a corner, scaling, collision-based inference or using a palette-only substitute. Aliases require identical full RGBA, native behavior and every native layer. Source maps, collision, warps and events are unchanged.')
                row['reverseGen2KantoReview']=dict(kind='explicit_whole_cliff_family',pixel_scale=1,approved_forward=dict(module=origin[0],index=origin[1]),source_module=mid,native_references=anchors)
            inventory.append(dict(mid=mid,ref=ref,origin=origin,anchors=anchors))
        (self.out/'whole-cliff-family-evidence.json').write_text(json.dumps(inventory,indent=2))
        layout=((104,105,106),(112,113,114),(120,121,122))
        before=Image.new('RGBA',(48,48));after=before.copy()
        for y,ids in enumerate(layout):
            for x,mid in enumerate(ids):
                m,b,q,_=CLIFF_MODULES[mid];after.paste(self.gb_image(self.gb_ref('crystal',m,b,q)),(x*16,y*16))
                anchor=next(v for v in inventory if v['mid']==mid)['anchors'][0]
                before.paste(preview.native_donor(self.cache,anchor,self.packed),(x*16,y*16))
        panel=Image.new('RGB',(48*8+24,48*4+28),'#18212b');panel.paste(before.resize((192,192),Image.Resampling.NEAREST),(4,24));panel.paste(after.resize((192,192),Image.Resampling.NEAREST),(208,24));panel.save(self.out/'whole-cliff-family-comparison.png')

    def paved_paths_and_fences(self):
        path=self.gb_at('crystal','PALLET_TOWN',2,3)
        fence=self.gb_ref('crystal','PALLET_TOWN',119,2)
        for mid in(357,358,359,365,366,367,373,374,375,405,406,413,414,212,219,221,228,230,231):
            source=self.checked_native('viridian_outdoor',mid);is_fence=mid in(230,231)
            art=self.native(fence if is_fence else path,'classic_gen2_complete_horizontal_fence_pair'if is_fence else'classic_gen2_complete_outdoor_open_path')
            art['overMask']='0'*256
            for game,pair,target in aliases(self,dict(tileset='viridian_outdoor',id=mid,material=not is_fence)):
                key=game,'gen2',pair,target,None
                if(game,pair,target)not in self.usage or key in self.current or key in self.rows:continue
                row=self.row(game,pair,target,'gen2',art,
                    'Explicit native source-resolution outdoor '+('horizontal garden fence pair'if is_fence else'plain paved/sandy path surface or grass join')+' review. Complete Crystal Kanto counterpart retains original1:1 pixels. The original Crystal town style uses its own open path material across these ordinary paved/dirt joins; signs, stairs, arrows, house doors/frames and raised cliffs are excluded. Fences use the same complete original Crystal pair as the already complete Pallet garden boundary. Native movement, sign/warp interactions, maps, collision, encounters and scripts are unchanged; aliases require exact native RGBA, all native layers, behavior and reviewed walkability context.')
                row['reverseGen2KantoReview']=dict(kind='complete_paved_path_or_fence_family',pixel_scale=1,source_pair='viridian_outdoor',source_id=mid,source_signature=MANUAL_SOURCES['viridian_outdoor',mid])

    def forest_trees(self):
        from reverse_kanto_review import tree_art,TREE_SOURCE,runs
        ground=ground_ref(self,'gen2');gb,map_id,bid='crystal','NATIONAL_PARK',6
        # NationalPark(6,48) is a standalone actual PARK6 tree with field
        # above. Its original32x32 canopy is complete, deliberately flat.
        standalone=Image.new('RGBA',(32,32))
        for q in range(4):standalone.paste(self.gb_image(self.gb_at('crystal','NATIONAL_PARK',6+q%2,48+q//2)),(q%2*16,q//2*16))
        assert all(self.gb_at('crystal','NATIONAL_PARK',6+q%2,48+q//2)['id']==6 for q in range(4))
        assert all(self.gb_at('crystal','NATIONAL_PARK',6+q%2,48+q//2)['hash']==PARK_TREE_HASHES[q]for q in range(4))
        original=standalone
        # Shared greens can connect grass directly to leaves, so a chroma/flood
        # mask would erase the canopy. These original silhouette row bounds
        # were reviewed against the complete standalone source and shadow.
        outside={(x,y)for y,(left,right)in enumerate(PARK_TREE_BOUNDS)for x in range(32)if x<left or x>right}
        background=set(self.gb_image(self.gb_at('crystal','NATIONAL_PARK',0,38)).get_flattened_data())|{(222,255,222,255)}
        assert all(original.getpixel(p)in background for p in outside)
        assert 1024-len(outside)==774
        self._park_tree=original,outside
        dense=Image.new('RGBA',(32,32))
        for q in range(4):
            ref=self.gb_at('crystal','ILEX_FOREST',4+q%2,16+q//2)
            assert ref['id']==5 and ref['hash']==FOREST_TREE_HASHES[q]
            dense.paste(self.gb_image(ref),(q%2*16,q//2*16))
        dense_outside={(x,y)for y,(left,right)in enumerate(FOREST_TREE_BOUNDS)for x in range(32)if x<left or x>right}
        colors=set(self.gb_image(self.gb_at('crystal','ILEX_FOREST',4,15)).get_flattened_data())|{(222,255,222,255)}
        assert all(dense.getpixel(point)in colors for point in dense_outside)
        assert 1024-len(dense_outside)==836
        self._dense_tree=dense,dense_outside
        models,masks,whole=self.wide_park_models(48)
        original,outside=self._dense_tree
        self._park_48_models=models;self._park_48_masks=masks
        # All native source tree cells are blocked. Complete caps/root remain
        # intact; only middle foliage/plain-shadow bands fill the envelope.
        cells={648:(0,0),649:(1,0),650:(2,0),656:(0,1),657:(1,1),658:(2,1),664:(0,0),665:(1,0),666:(2,0),672:(0,1),673:(1,1),674:(2,1),675:(0,2),676:(1,2),677:(2,2)}
        pair='general__rom_082d4dc4';proof=[]
        for mid,xy in cells.items():
            src=self.checked_native(pair,mid)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                c=self.imp.cell_index(game)[tp,tm];over=preview.native_donor(self.cache,dict(game=game,tileset=tp,id=tm,hash=c['pixel_sha256']),self.packed,['over'],{'over':c['layer_sha256']['over']})
                has_over=any(p[3]for p in over.get_flattened_data());art=copy.deepcopy(models[xy]);art['overMask']=''.join('1'if keep and has_over else'0'for keep in masks[xy])
                self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,
                    'Complete original Crystal FOREST5 tree, verified in standalone actual Ilex cells(4,16)-(5,17), with ordinary field directly above at(4,15)-(5,15). The complete original crown, outer caps, trunk and roots retain1:1 native pixels inside the full48x48 blocked FR envelope. Only complete8px middle-foliage bands and plain matching shadow extend its width/height; no source row becomes an invisible blocked grass tile. Only the reviewed native exterior-field silhouette is masked onto matching classic ground; leaf greens cannot be removed by a color flood. Continuing source canopy/root overlaps use the corresponding intact native crown/root rows. Source walkable canopy, blocked root cells, source overhead priority, actors, grass/cut interactions, collision and events stay unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_native_forest_tree_root_anchor',pixel_scale=1,native_dimensions=[32,32],host_envelope=[48,48],native_middle_foliage_band=[8,8],inserted_foliage_rows=16,source_pair=pair,source_id=mid,source_signature=MANUAL_SOURCES[pair,mid],source_over_pixels=sum(p[3]>0 for p in over.get_flattened_data()),target_section=list(xy),native_standalone_witness=dict(map='ILEX_FOREST',x=4,y=16,w=2,h=2))
                proof.append(dict(game=game,pair=tp,id=tm,target_section=list(xy),source_over_pixels=sum(p[3]>0 for p in over.get_flattened_data())))
        checks=0
        for y in range(32):
            for x in range(32):
                if(x,y)not in outside:assert whole.getpixel((x if x<8 else x+8 if x<24 else x+16,y if y<8 else y+16))==original.getpixel((x,y));checks+=1
        source=Image.new('RGBA',(48,48))
        for y,ids in enumerate(((648,649,650),(672,673,674),(675,676,677))):
            for x,mid in enumerate(ids):
                c=self.checked_native(pair,mid);source.paste(preview.native_donor(self.cache,dict(game='firered',tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed),(x*16,y*16))
        panel=Image.new('RGB',(792,408),'#18212b');panel.paste(source.resize((384,384),Image.Resampling.NEAREST),(4,24));panel.paste(whole.resize((384,384),Image.Resampling.NEAREST),(400,24));panel.save(self.out/'complete-forest-tree-comparison.png')
        (self.out/'complete-forest-tree-evidence.json').write_text(json.dumps(dict(native_foreground_pixels_preserved=checks,rows=proof),indent=2))

    def wide_park_models(self,height):
        assert height in(48,64)
        original,outside=self._dense_tree;ground=ground_ref(self,'gen2')
        shadow=copy.deepcopy(self._black_ref);shadow['monochrome']=False
        shadow['palettes']=[[[222,255,222],[197,148,58],[165,123,25],[58,58,58]]for _ in range(8)]
        assert set(self.gb_image(shadow).get_flattened_data())=={(58,58,58,255)}
        models={};masks={};whole=Image.new('RGBA',(48,height))
        def source_y(y):return y if y<8 else 8+(y-8)%8 if y<height-24 else y-(height-32)
        def source_x(x):return x if x<8 else x if x<16 else x-8 if x<32 else x-16
        def pixel_kind(x,y):
            sy=source_y(y);insert=x//8 in(1,4)
            if insert and sy>=24:
                left,right=FOREST_TREE_BOUNDS[sy];point=8 if x//8==1 else 23
                return 'shadow'if sy>=24 and left<=point<=right else'field'
            return 'tree'if(source_x(x),sy)not in outside else'field'
        for cy in range(height//16):
            for cx in range(3):
                pieces=[];shade=[];mask=[pixel_kind(cx*16+x,cy*16+y)!='field'for y in range(16)for x in range(16)]
                tree_mask=[pixel_kind(cx*16+x,cy*16+y)=='tree'for y in range(16)for x in range(16)];shadow_mask=[pixel_kind(cx*16+x,cy*16+y)=='shadow'for y in range(16)for x in range(16)]
                for dy in(0,8):
                    for dx in(0,8):
                        gx,gy=cx*16+dx,cy*16+dy;sx,sy=source_x(gx),source_y(gy)
                        ref=self.gb_ref('crystal','ILEX_FOREST',5,sy//16*2+sx//16)
                        pieces.append(dict(donor=ref,x=dx,y=dy,w=8,h=8,srcX=sx%16,srcY=sy%16))
                        shade.append(dict(donor=shadow,x=dx,y=dy,w=8,h=8,srcX=0,srcY=0))
                parts=clip_parts(pieces,tree_mask)+clip_parts(shade,shadow_mask);assert 0<len(parts)<=32,(height,cx,cy,len(parts))
                art=self.composite(ground,parts,'classic_gen2_complete_native_forest_tree_'+str(height)+'_'+str(cx)+'_'+str(cy));models[cx,cy]=art;masks[cx,cy]=mask;whole.paste(self.render(art),(cx*16,cy*16))
                assert mask[8*16+8],('A blocked native tree cell center would be invisible',height,cx,cy)
        checks=0
        for y in range(32):
            for x in range(32):
                if(x,y)in outside:continue
                dx=x if x<8 else x+8 if x<24 else x+16;dy=y if y<8 else y+(height-32)
                assert whole.getpixel((dx,dy))==original.getpixel((x,y)),(height,x,y);checks+=1
        assert checks==836
        (self.out/('park-complete-'+str(height)+'-module-proof.json')).write_text(json.dumps(dict(native_source='TILESET_FOREST5',native_source_pixels_preserved=checks,host=[48,height],whole_original_crown_root=True,plain_shadow_and_complete_8px_foliage_only=True,all_blocked_cell_centers_covered=True),indent=2))
        return models,masks,whole

    def safari_trees(self):
        pair='general__rom_082d4b54';models,masks,full=self.wide_park_models(64)
        cells={757:(0,2),758:(1,2),759:(2,2),765:(0,1),766:(1,1),767:(2,1),773:(0,2),774:(1,2),775:(2,2),781:(0,3),782:(1,3),783:(2,3),789:(0,0),790:(1,0),791:(2,0),797:(0,1),798:(1,1),799:(2,1),805:(0,1),806:(1,1),807:(2,1)};proof=[]
        for mid,xy in cells.items():
            self.checked_native(pair,mid)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                c=self.imp.cell_index(game)[tp,tm];over=preview.native_donor(self.cache,dict(game=game,tileset=tp,id=tm,hash=c['pixel_sha256']),self.packed,['over'],{'over':c['layer_sha256']['over']});has_over=any(p[3]for p in over.get_flattened_data())
                art=copy.deepcopy(models[xy]);art['overMask']=''.join('1'if keep and has_over else'0'for keep in masks[xy]);self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,'Complete original native Crystal FOREST5 tree replaces the complete Safari tropical-tree assembly at1:1 native pixels. The native source standalone tree is48x64 (true cap789-791, upper foliage797-799, lower canopy773-775, root781-783); the full original classic crown/root remain at1:1, with only complete8px middle-foliage bands and plain shadow filling the original48x64 blocked envelope. Dense overlapping source crown/root variants become the corresponding complete classic canopy/root rows, retaining all836 original native tree/shadow pixels without a resize or clipped crown/root. Every source blocked cell center is visibly tree or its matching shadow. Only reviewed source field outside the silhouette is masked; native upper-canopy walkability, lower blocking, overhead ordering, grass/Surf/actors/events and collisions remain unchanged. Rock/water/house/cut/border fragments are not inferred as trees.')
                row['reverseGen2KantoReview']=dict(kind='complete_safari_tree_native_park_counterpart',pixel_scale=1,native_dimensions=[32,32],host_envelope=[48,64],native_middle_foliage_band=[8,8],inserted_foliage_rows=32,native_tree_pixels_preserved=836,source_pair=pair,source_id=mid,source_signature=MANUAL_SOURCES[pair,mid],target_section=list(xy),source_over_pixels=sum(p[3]>0 for p in over.get_flattened_data()))
                proof.append(dict(game=game,pair=tp,id=tm,target_section=list(xy)))
        native=Image.new('RGBA',(48,64));after=native.copy()
        for y,ids in enumerate(((789,790,791),(797,798,799),(773,774,775),(781,782,783))):
            for x,mid in enumerate(ids):
                c=self.checked_native(pair,mid);native.paste(preview.native_donor(self.cache,dict(game='firered',tileset=pair,id=mid,hash=c['pixel_sha256']),self.packed),(x*16,y*16));after.paste(self.render(models[x,y]),(x*16,y*16))
        original,outside=self._dense_tree
        assert all(after.getpixel((x if x<8 else x+8 if x<24 else x+16,y if y<8 else y+32))==original.getpixel((x,y))for y in range(32)for x in range(32)if(x,y)not in outside)
        panel=Image.new('RGB',(792,536),'#18212b');panel.paste(native.resize((384,512),Image.Resampling.NEAREST),(4,24));panel.paste(after.resize((384,512),Image.Resampling.NEAREST),(400,24));panel.save(self.out/'complete-safari-tree-comparison.png')
        (self.out/'complete-safari-tree-evidence.json').write_text(json.dumps(proof,indent=2))

    def verified_park_tree_upgrades(self):
        from reverse_kanto_review import runs
        original,outside=self._park_tree;supersessions=[];proof=[]
        for game,pair,mid,q,source_hash,source_behavior in TREE32_TARGETS:
            assert game in GAMES
            source=self.imp.cell_index(game)[pair,mid]
            assert source['pixel_sha256']==source_hash and source['behavior']==source_behavior,(game,pair,mid)
            if(game,pair,mid)not in self.usage:continue
            ref=self.gb_ref('crystal','NATIONAL_PARK',6,q);assert ref['hash']==PARK_TREE_HASHES[q]
            mask=[(q%2*16+x,q//2*16+y)not in outside for y in range(16)for x in range(16)]
            parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)];assert 0<len(parts)<=32
            art=self.composite(ground_ref(self,'gen2'),parts,'classic_gen2_verified_complete_park_tree32_'+str(q));art['overMask']=''.join('1'if v else'0'for v in mask)
            key=game,'gen2',pair,mid,None;old=self.current.get(key)
            if old:
                assert old['role']=='classic_complete_native_tree32_'+str(q),(key,old['role'])
                module,index=self.origins[id(old)]
                supersessions.append(dict(oldmodule=module,oldindex=index,oldrow=copy.deepcopy(old),oldrow_sha256=catalog.sha(stable(old).encode()),newkey=list(key)))
            self.rows.pop(key,None)
            row=self.row(game,pair,mid,'gen2',art,
                'Verified complete original Crystal NationalPark PARK6 tree provides a complete original native variant in this already-reviewed32px tree family; FOREST5 is independently verified complete too, so no missing cap is inferred. The actual standalone tree at cells(6,48)-(7,49) has field above, establishing its complete canopy, trunk and shadow. All original native pixels stay1:1; a reviewed silhouette keeps every leaf/frame/wood pixel and removes only original exterior field. Exact original source RGBA and behavior guards and the previously reviewed whole-tree quadrant correspondence remain unchanged. Source map, blocking, actors, interactions and scripts are unchanged; Gen1 theme is untouched.')
            row['reverseGen2KantoReview']=dict(kind='verified_complete_park_tree32_upgrade',pixel_scale=1,native_dimensions=[32,32],native_map='NATIONAL_PARK',native_block=6,quadrant=q,whole_tree_retained_native_pixels=774,native_mask_bounds=PARK_TREE_BOUNDS)
            proof.append(dict(game=game,pair=pair,id=mid,quadrant=q,source_hash=source_hash))
        indices={identity(r):i for i,r in enumerate(self.rows.values(),1)}
        for v in supersessions:
            key=tuple(v.pop('newkey'));v.update(newmodule='mappings/reverse_gen2_kanto_finish.lua',newindex=indices[key],newrow=copy.deepcopy(self.rows[key]))
        (self.out/'exact-old-row-supersessions.json').write_text(json.dumps(supersessions,indent=2))
        (self.out/'verified-park-tree-upgrades.json').write_text(json.dumps(dict(source_native_pixels_preserved=774,rows=proof),indent=2))

    def tree_collision_review(self):
        checked=[];counts=Counter();profiles=defaultdict(Counter);kinds=('complete_native_forest_tree_root_anchor','complete_safari_tree_native_park_counterpart','verified_complete_park_tree32_upgrade')
        for(game,name),(spec,layout)in self.layouts.items():
            pair=spec['pair'];selected={mid:self.rows.get((game,'gen2',pair,mid,None))for mid in set(layout['mids'])}
            selected={mid:r for mid,r in selected.items()if r and r.get('reverseGen2KantoReview',{}).get('kind')in kinds}
            if not selected:continue
            path=self.cache/game/'data/generated/gba/native'/spec['file'];data=path.read_bytes();raw=data if data[:4]==b'SVML'else zlib.decompress(data);pw,ph=struct.unpack_from('<HH',raw,6);offset=16+raw[14]*raw[15]*2
            contexts=[]
            for y in range(layout['height']):
                for x in range(layout['width']):
                    mid=layout['mids'][y*layout['width']+x];row=selected.get(mid)
                    if row is None:continue
                    permission=raw[offset+(y*pw+x)*4+2];walkable=bool(self.imp.permissions.isWalkable(permission));profiles[game,pair,mid][str(permission)]+=1
                    # Native permission remains solely in the unchanged source
                    # layout. Every blocked center must be visible tree/shadow.
                    if not walkable:
                        assert row['overMask'][136]in'01'
                        target=self.render(row).getpixel((8,8));base=self.gb_image(ground_ref(self,'gen2')).getpixel((8,8))
                        assert target!=base,('Invisible blocked tree center',game,name,x,y,mid)
                    counts[game]+=1
                    contexts.append(dict(x=x,y=y,id=mid,permission=permission,walkable=walkable))
            assert path.read_bytes()==data
            checked.append(dict(game=game,map=name,pair=pair,source_layout_sha256=catalog.sha(data),source_data_unchanged=True,cells=contexts))
        (self.out/'tree-collision-and-footprint-evidence.json').write_text(json.dumps(dict(counts=dict(counts),profiles=[dict(game=k[0],pair=k[1],id=k[2],permissions=dict(v))for k,v in profiles.items()],all_original_blocked_centers_visible=True,maps=checked),indent=2))

    def clear_material_extensions(self):
        from reverse_kanto_review import runs
        defs={
            ('building__rom_082d5094',750):('BATTLE_TOWER_BATTLE_ROOM',10,0,'trainer_tower_battle_floor'),
            ('building__rom_082d4f8c',641):('CELADON_MANSION_1F',3,0,'condominium_medallion_floor'),
            ('building__rom_082d4d7c',641):('SAFFRON_GYM',15,0,'gym_checkered_floor'),
            ('house',642):('PLAYERS_HOUSE_1F',3,0,'house_checkered_wood_floor'),
            ('house',273):('PLAYERS_HOUSE_1F',3,0,'house_horizontal_wood_floor'),
            ('general__rom_082d4d94',804):('FAST_SHIP_1F',4,0,'ship_cabin_floor'),
            ('general__rom_082d4b3c',808):('SAFFRON_CITY',119,0,'cycling_road_paving_left'),
            ('general__rom_082d4b3c',809):('SAFFRON_CITY',119,0,'cycling_road_paving_middle'),
            ('general__rom_082d4b3c',810):('SAFFRON_CITY',119,0,'cycling_road_paving_right'),
            ('general__rom_082d4b3c',830):('PALLET_TOWN',1,0,'cycling_road_field'),
            ('general__rom_082d4b3c',831):('PALLET_TOWN',1,0,'cycling_road_field_plain'),
            ('general__rom_082d4b3c',190):('PALLET_TOWN',1,0,'ordinary_city_worn_lawn'),
            ('general__rom_082d4b3c',198):('PALLET_TOWN',1,0,'ordinary_city_open_lawn_tufts')}
        proof=[]
        for(pair,mid),(name,b,q,role)in defs.items():
            if(pair,mid)not in MANUAL_SOURCES:continue
            src=self.checked_native(pair,mid);ref=self.gb_ref('crystal',name,b,q)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid,material=True)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                c=self.imp.cell_index(game)[tp,tm];over=preview.native_donor(self.cache,dict(game=game,tileset=tp,id=tm,hash=c['pixel_sha256']),self.packed,['over'],{'over':c['layer_sha256']['over']})
                assert not any(p[3]for p in over.get_flattened_data()),(tp,tm)
                art=self.native(ref,'classic_gen2_complete_'+role);art['overMask']='0'*256;self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,'Actual complete room/town source material reviewed at native resolution: '+role+'. An original Crystal ordinary floor/field/paving motif is selected coherently for the corresponding source context, with every original pixel retained at1:1. No unique icon, cabinet, staircase, rug border or puzzle marker is inferred as plain floor. Source cycling/walkability, encounters, scripts and native map/event/collision data are unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_contextual_floor_or_ground',pixel_scale=1,source_pair=pair,source_id=mid,source_signature=MANUAL_SOURCES[pair,mid])
                proof.append(dict(game=game,pair=tp,id=tm,role=role))
        # Staff-side clinic floor is separately verified original red checker,
        # not the public cream/pink floor and not a counter/terminal fragment.
        ref=self.gb_at('crystal','AZALEA_POKECENTER_1F',3,1)
        for game in GAMES:
            pair='network';mid=695;key=game,'gen2',pair,mid,None
            if key in self.current or(game,pair,mid)not in self.usage:continue
            self.checked_native(pair,mid);art=self.native(ref,'classic_gen2_complete_clinic_staff_floor');art['overMask']='0'*256;self.rows.pop(key,None)
            row=self.row(game,pair,mid,'gen2',art,'Complete original staff-side Crystal clinic floor at Azalea(3,1), checked to contain only its red/pink checker motif. This stays distinct from the public cream/pink diamond floor. The entire original native16px pattern stays1:1 and the original source counter, heal interactions, collision, warp and actors are unchanged.')
            row['reverseGen2KantoReview']=dict(kind='complete_clinic_staff_floor',pixel_scale=1,source_signature=MANUAL_SOURCES[pair,mid],original_crystal_cell=[3,1])
        # Native vertical low curbs: complete Saffron8px bars preserve their
        # highlights; the remaining8px is matching classic field, not old floor.
        for mid,b,q,qs in((244,39,0,(0,2)),(245,39,1,(1,3))):
            pair='general__rom_082d4b3c';src=self.checked_native(pair,mid);ref=self.gb_ref('crystal','SAFFRON_CITY',b,q)
            mask=[(y//8*2+x//8)in qs for y in range(16)for x in range(16)];parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)]
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                art=self.composite(ground_ref(self,'gen2'),parts,'classic_gen2_complete_low_vertical_curb_'+str(mid));art['overMask']='0'*256;self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,'Reviewed native low gray/white vertical city curb, separate from tall fence posts. Complete original Crystal Saffron8px vertical bar glyphs retain their pale highlight stripe and original handed direction at1:1. Remaining pixels use the matching classic field, so no native source grass/floor rectangle leaks. Original route openings, blocked edge and all source semantics are unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_native_low_city_curb',pixel_scale=1,source_signature=MANUAL_SOURCES[pair,mid],direction='west'if mid==244 else'east')
        # Plain straight additional height of the already reviewed cliff family.
        for mid,parent in((115,112),(117,114),(124,121)):
            pair='general__rom_082d507c';self.checked_native(pair,mid);name,b,q,_=CLIFF_MODULES[parent];ref=self.gb_ref('crystal',name,b,q)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                art=self.native(ref,'classic_gen2_complete_tall_cliff_face_'+str(mid));art['overMask']='0'*256;self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,'Actual native extended straight cliff face reviewed in the joined source family. Left115, right117 and full front124 repeat the matching complete Crystal Kanto left/right/south face module at1:1; source rock top, walking ground, inward/outward corners, mouths, stairs and jump ledges remain separately reviewed. No new corner or cropped cap is invented. Source collision, elevation and all maps/events remain unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_extended_cliff_face',pixel_scale=1,source_signature=MANUAL_SOURCES[pair,mid],parent_reviewed_directional_module=parent)
        (self.out/'clear-material-extension-evidence.json').write_text(json.dumps(proof,indent=2))

    def materials(self):
        for(game,pair,mid),usage in self.usage.items():
            key=game,'gen2',pair,mid,None
            if key in self.current:continue
            src=self.imp.cell_index(game)[pair,mid];spec=MATERIALS.get(src['pixel_sha256'])
            if spec is None:continue
            name,b,q,role=spec;ref=self.gb_ref('crystal',name,b,q)
            source=dict(game=game,tileset=pair,id=mid,hash=src['pixel_sha256'])
            over=preview.native_donor(self.cache,source,self.packed,['over'],{'over':src['layer_sha256']['over']})
            if any(p[3]for p in over.get_flattened_data()):
                self.held.append(dict(reason='Material unexpectedly has overhead art',game=game,pair=pair,id=mid));continue
            art=self.native(ref,'classic_gen2_reviewed_'+role);art['overMask']='0'*256
            self.rows.pop(key,None)
            row=self.row(game,pair,mid,'gen2',art,
                'Explicit whole16px material family review in the native FR/LG cave/room/town inventory: '+role+'. This is a complete plain surface; source solid raised rock, ordinary walkable cave floor, ruin stone paving, snow and nonencounter field/path are reviewed separately. Crystal native original material is retained at1:1. No directional walls, structures, props, ice-slide surfaces, shadows containing unique objects, or encounter grass are inferred from collision. Source movement, maps, warps, events and scripts remain unchanged.')
            row['reverseGen2KantoReview']=dict(kind='reviewed_complete_material',pixel_scale=1,
                source_rgba_sha256=src['pixel_sha256'],original_crystal_rgba_sha256=catalog.sha(self.gb_image(ref).tobytes()),usage=usage)

    def small_decorative_trees(self):
        from reverse_kanto_review import runs
        ref=self.gb_ref('crystal','NEW_BARK_TOWN',98,1)
        assert ref['hash']=='f432dde58cfac9e2a6549aec5428277ae0bb8c002d481a3f13e47f13a7eb8f69'
        original=self.gb_image(ref);bounds=((7,8),(6,9),(6,9),(5,10),(3,12),(2,13),(2,13),(2,13),(0,15),(1,14),(2,13),(3,12),(5,10),(4,11),(6,9),(7,8))
        mask=[left<=x<=right for y,(left,right)in enumerate(bounds)for x in range(16)]
        field=set(self.gb_image(self.gb_ref('crystal','NEW_BARK_TOWN',2,0)).get_flattened_data())
        assert all(mask[y*16+x]or original.getpixel((x,y))in field for y in range(16)for x in range(16))
        assert all(mask[y*16+x]for y in range(16)for x in range(16)if original.getpixel((x,y))==(58,58,58,255))
        parts=[dict(donor=ref,srcX=p['x'],srcY=p['y'],**p)for p in runs(mask)];assert 0<len(parts)<=32
        base=ground_ref(self,'gen2');art0=self.composite(base,parts,'classic_gen2_complete_native_small_decorative_tree');proof=[]
        for pair,mid in(('general__rom_082d4b3c',5),('general__rom_082d4b54',756)):
            self.checked_native(pair,mid)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                c=self.imp.cell_index(game)[tp,tm];over=preview.native_donor(self.cache,dict(game=game,tileset=tp,id=tm,hash=c['pixel_sha256']),self.packed,['over'],{'over':c['layer_sha256']['over']})
                art=copy.deepcopy(art0);art['overMask']=''.join('1'if p and any(c[3]for c in over.get_flattened_data())else'0'for p in mask);self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,'Actual small round decorative boundary shrub uses the complete native Crystal16px small-tree counterpart (NewBark98q1, also actual Route29 60q0). Full crown, native small base and every dark outline pixel stay1:1. The explicitly reviewed closed tree silhouette removes only exterior native field colors, so source grass cannot become a green floor rectangle. This does not confer Headbutt or Cut: the original native decorative blocking/interactions, NPCs, maps and scripts remain unchanged. Larger forest trees, stumps and terrain are separate.')
                row['reverseGen2KantoReview']=dict(kind='complete_small_decorative_tree',pixel_scale=1,native_dimensions=[16,16],source_signature=MANUAL_SOURCES[pair,mid],native_retained_pixels=sum(mask),native_silhouette_bounds=[list(v)for v in bounds])
                result=self.render(row);assert all(not mask[y*16+x]or result.getpixel((x,y))==original.getpixel((x,y))for y in range(16)for x in range(16))
                proof.append(dict(game=game,pair=tp,id=tm,native_pixels=sum(mask)))
        self.render(art0).resize((256,256),Image.Resampling.NEAREST).save(self.out/'complete-small-decorative-tree.png')
        (self.out/'complete-small-decorative-tree-evidence.json').write_text(json.dumps(proof,indent=2))

    def ordinary_caves(self):
        # These six complete native source families were reviewed as joined3x3
        # raised-rock banks, not inferred from matching movement/collision.
        pairs=('general__rom_082d4bfc','general__rom_082d4df4','general__rom_082d4e0c','general__rom_082d4e54','general__rom_082d4fec','general__rom_082d501c','general__rom_082d5004')
        cells={641:(2,0),648:(4,0),649:(4,1),650:(6,1),656:(4,2),657:(4,3),658:(6,3),664:(12,2),665:(12,3),666:(14,3),667:(16,3),668:(17,2),710:(4,2),711:(6,3)}
        proof=[]
        for pair in pairs:
            for mid,(b,q)in cells.items():
                if(pair,mid)not in MANUAL_SOURCES:continue
                src=self.checked_native(pair,mid);ref=self.gb_ref('crystal','UNION_CAVE_1F',b,q)
                for game,tp,tm in aliases(self,dict(tileset=pair,id=mid,material=mid in(641,657))):
                    key=game,'gen2',tp,tm,None
                    if(game,tp,tm)not in self.usage or key in self.current:continue
                    c=self.imp.cell_index(game)[tp,tm]
                    over=preview.native_donor(self.cache,dict(game=game,tileset=tp,id=tm,hash=c['pixel_sha256']),self.packed,['over'],{'over':c['layer_sha256']['over']})
                    opaque=sum(p[3]>0 for p in over.get_flattened_data())
                    if opaque not in(0,256):
                        self.held.append(dict(game=game,pair=tp,id=tm,reason='Cave candidate has partial overhead; complete feature review required',over_pixels=opaque));continue
                    art=self.native(ref,'classic_gen2_complete_cave_bank_'+str(mid));art['overMask']=('1'if opaque else'0')*256
                    self.rows.pop(key,None)
                    row=self.row(game,tp,tm,'gen2',art,
                        'Complete ordinary cave family reviewed in joined native3x3 source banks for MtMoon/LostCave/VictoryRoad, RockTunnel, Diglett, Cerulean, MtEmberRubyPath and NavelRock/DottedHole. Crystal UNION_CAVE supplies the corresponding full north/west/east/south banks, convex corners, concave nubs, raised rock top and walkable floor at native1:1. The whole joined family is coherent; snow/ice walls, cave mouths, ladder heads, button puzzles, holes and special stairs are separate. Source layer identity, all movement/warp/collision/event semantics remain native.')
                    row['reverseGen2KantoReview']=dict(kind='complete_joined_cave_bank_family',pixel_scale=1,source_pair=pair,source_id=mid,source_signature=MANUAL_SOURCES[pair,mid],original_crystal_block=b,original_crystal_quadrant=q)
                    proof.append(dict(game=game,pair=tp,id=tm,source_pair=pair,source_id=mid,original_crystal_block=b,original_crystal_quadrant=q))
        after=Image.new('RGBA',(48,48))
        for y,ids in enumerate(((648,649,650),(656,657,658),(664,665,666))):
            for x,mid in enumerate(ids):
                b,q=cells[mid];after.paste(self.gb_image(self.gb_ref('crystal','UNION_CAVE_1F',b,q)),(x*16,y*16))
        after.resize((384,384),Image.Resampling.NEAREST).save(self.out/'ordinary-cave-joined-crystal.png')
        (self.out/'ordinary-cave-family-evidence.json').write_text(json.dumps(proof,indent=2))

    def ice_cave_family(self):
        pair='general__rom_082d4e24';cells={641:(4,3),648:(25,0),649:(4,1),650:(25,1),656:(8,0),657:(42,2),658:(10,1),664:(25,2),665:(13,2),666:(25,3),667:(16,3),668:(17,2)};proof=[]
        bank=Image.new('RGBA',(48,48));positions={}
        for yy,ids in enumerate(((648,649,650),(656,657,658),(664,665,666))):
            for xx,mm in enumerate(ids):
                bb,qq=cells[mm];bank.paste(self.gb_image(self.gb_ref('crystal','ICE_PATH_1F',bb,qq)),(xx*16,yy*16));positions[mm]=xx,yy
        snow_colors=set(self.gb_image(self.gb_ref('crystal','ICE_PATH_1F',4,3)).get_flattened_data());outside=exterior(bank,snow_colors)
        assert(24,24)not in outside
        for mid,(b,q)in cells.items():
            src=self.checked_native(pair,mid);ref=self.gb_ref('crystal','ICE_PATH_1F',b,q)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid,material=mid in(641,657))):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                c=self.imp.cell_index(game)[tp,tm];over=preview.native_donor(self.cache,dict(game=game,tileset=tp,id=tm,hash=c['pixel_sha256']),self.packed,['over'],{'over':c['layer_sha256']['over']})
                opaque=sum(p[3]>0 for p in over.get_flattened_data())
                if opaque not in(0,256):
                    self.held.append(dict(game=game,pair=tp,id=tm,reason='Ice bank has partial source priority requiring complete silhouette review',over_pixels=opaque));continue
                art=self.native(ref,'classic_gen2_complete_joined_ice_bank_'+str(mid))
                if opaque==256:
                    if mid in positions:
                        xx,yy=positions[mid];mask=[(xx*16+x,yy*16+y)not in outside for y in range(16)for x in range(16)]
                    else:
                        local_outside=exterior(self.gb_image(ref),snow_colors);mask=[(x,y)not in local_outside for y in range(16)for x in range(16)]
                    art['overMask']=''.join('1'if bit else'0'for bit in mask)
                else:art['overMask']='0'*256
                self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,'Complete snowy/ice cave bank family reviewed as a joined whole3x3 source island. Native Crystal ICE_PATH provides one coherent set of original convex corners, straight banks, raised icy top, inner nubs and ordinary snow floor at1:1. Complete original block25 supplies its matching four corners; straight original bank modules fill the native source width without scaling, mirrored shading or cut caps. Polished sliding ice, boulders, ladders, holes and waterfall puzzles are separate. Source snow/slide collision and all original native map/event/warp/actor data remain unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_joined_ice_bank_family',pixel_scale=1,source_pair=pair,source_id=mid,source_signature=MANUAL_SOURCES[pair,mid],original_crystal_map='ICE_PATH_1F',original_crystal_block=b,original_crystal_quadrant=q,native_over_pixels=opaque,raised_island_outside_only=True)
                proof.append(dict(game=game,pair=tp,id=tm,block=b,quadrant=q))
        (self.out/'ice-cave-family-evidence.json').write_text(json.dumps(proof,indent=2))

    def reviewed_room_materials(self):
        # Full-source-resolution surfaces and uninterrupted wall bands reviewed
        # in their actual tower, Silph, Mansion, Safari office and Sevii rooms.
        defs={
            ('building__rom_082d4ecc',821):('SILPH_CO_1F',7,0,'office_panel_floor'),
            ('building__rom_082d4ecc',816):('SILPH_CO_1F',1,0,'office_back_wall_band'),
            ('building__rom_082d4ecc',824):('SILPH_CO_1F',1,0,'office_back_wall_foot'),
            ('building__rom_082d4ecc',656):('TEAM_ROCKET_BASE_B1F',10,3,'rocket_right_partition_boundary'),
            ('building__rom_082d4ecc',660):('TEAM_ROCKET_BASE_B1F',10,3,'rocket_right_partition_boundary_lower'),
            ('building__rom_082d4ecc',642):('TEAM_ROCKET_BASE_B2F',54,2,'rocket_floor'),
            ('building__rom_082d4efc',642):('SAFFRON_GYM',15,0,'tower_stone_diamond_floor'),
            ('building__rom_082d4f2c',644):('RUINS_OF_ALPH_AERODACTYL_CHAMBER',5,3,'mansion_regular_stone_floor'),
            ('building__rom_082d4f2c',645):('RUINS_OF_ALPH_AERODACTYL_CHAMBER',5,3,'mansion_stone_floor_joint'),
            ('building__rom_082d4f2c',646):('PLAYERS_HOUSE_1F',3,0,'mansion_basement_wood_floor'),
            ('building__rom_082d4f2c',690):('PLAYERS_HOUSE_1F',5,0,'mansion_panelled_wall_base'),
            ('building__rom_082d4f2c',674):('PLAYERS_HOUSE_1F',5,0,'mansion_horizontal_wall'),
            ('building__rom_082d4f2c',682):('PLAYERS_HOUSE_1F',5,0,'mansion_plain_wall'),
            ('building__rom_082d4f14',656):('PLAYERS_HOUSE_1F',3,0,'safari_wood_floor'),
            ('general__rom_082d4b9c',745):('SAFFRON_CITY',119,0,'saffron_paved_walking_ground'),
            ('sevii_outdoor',849):('UNION_CAVE_1F',2,0,'volcanic_gray_stone_walking_ground'),
            ('sevii_outdoor',851):('UNION_CAVE_1F',4,3,'volcanic_raised_rock_top'),
            ('sevii_outdoor',853):('UNION_CAVE_1F',6,3,'volcanic_rock_east_face'),
            ('sevii_outdoor',860):('UNION_CAVE_1F',4,3,'volcanic_solid_raised_rock')}
        proof=[]
        for(pair,mid),(name,b,q,role)in defs.items():
            src=self.checked_native(pair,mid);ref=self.gb_ref('crystal',name,b,q)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid,material='floor'in role or 'walking_ground'in role)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                c=self.imp.cell_index(game)[tp,tm]
                source=dict(game=game,tileset=tp,id=tm,hash=c['pixel_sha256'])
                over=preview.native_donor(self.cache,source,self.packed,['over'],{'over':c['layer_sha256']['over']})
                opaque=sum(p[3]>0 for p in over.get_flattened_data())
                if opaque not in(0,256):continue
                art=self.native(ref,'classic_gen2_native_'+role)
                if role.startswith('rocket_right_partition_boundary'):
                    floor=self.gb_ref('crystal','TEAM_ROCKET_BASE_B2F',54,2)
                    art=self.composite(floor,[dict(donor=ref,x=8,y=0,srcX=8,srcY=0,w=8,h=16)],'classic_gen2_native_'+role)
                elif role=='office_back_wall_band':
                    art=self.composite(None,[dict(donor=ref,x=0,y=0,srcX=0,srcY=0,w=16,h=8),dict(donor=ref,x=0,y=8,srcX=0,srcY=4,w=16,h=8)],'classic_gen2_native_'+role)
                elif role=='office_back_wall_foot':
                    floor=self.gb_ref('crystal','SILPH_CO_1F',7,0)
                    art=self.composite(floor,[dict(donor=ref,x=0,y=0,srcX=0,srcY=8,w=16,h=8)],'classic_gen2_native_'+role)
                art['overMask']=('1'if opaque else'0')*256
                self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,'Explicit actual whole-room/material-family review: '+role+'. The complete Crystal ordinary floor/wall module is retained at native1:1, with one coherent material per source family. No uniquely functional puzzle, feature or prop is inferred from movement. Full native source RGBA/layers/behavior and destination map context are checked; source collision, interactions, warps and events are unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_room_material',pixel_scale=1,source_pair=pair,source_id=mid,source_signature=MANUAL_SOURCES[pair,mid],original_crystal_map=name,original_crystal_block=b,original_crystal_quadrant=q)
                proof.append(dict(game=game,pair=tp,id=tm,role=role,original_crystal_map=name,block=b,quadrant=q))
        (self.out/'room-material-evidence.json').write_text(json.dumps(proof,indent=2))

    def spin_floor_symbols(self):
        proof=[]
        # The original GSC Viridian Gym floor is a complete ordinary blue
        # checker. Its actual82-cell source dominance and full layout were
        # independently reviewed; no spin/arrow behavior is borrowed from it.
        gym_floor=self.gb_ref('crystal','VIRIDIAN_GYM',3,0)
        assert self.imp.cell_index('crystal')[gym_floor['tileset'],3,0]['collision']==0
        for mid in(641,642):
            pair='building__rom_082d4cbc';self.checked_native(pair,mid)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid,material=True)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage or key in self.current:continue
                art=self.native(gym_floor,'classic_gen2_native_viridian_gym_ordinary_floor');art['overMask']='0'*256;self.rows.pop(key,None)
                row=self.row(game,tp,tm,'gen2',art,'Explicit actual Viridian Gym ordinary floor, reviewed in the full native source maze and original Crystal room. Native source641/642 are two appearances of the same clear blue/tiled walking floor, separate from walls, rugs, spinner panels and stop cells. The original Crystal VIRIDIAN_GYM3q0 complete16px floor stays1:1; native movement/spin puzzle/actor/collision/event data are unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_contextual_floor_or_ground',pixel_scale=1,source_signature=MANUAL_SOURCES[pair,mid],native_gsc_floor=gym_floor)
        for pair,mid,direction in SPIN_SYMBOLS:
            src=self.checked_native(pair,mid);hint=src['behavior_hint'];expected={'north':'MB_SPIN_UP','east':'MB_SPIN_RIGHT','south':'MB_SPIN_DOWN','west':'MB_SPIN_LEFT','stop':'MB_STOP_SPINNING'}[direction];assert hint==expected
            floor=gym_floor if pair=='building__rom_082d4cbc'else self.gb_ref('crystal','TEAM_ROCKET_BASE_B2F',54,2)
            assert self.imp.cell_index('crystal')[floor['tileset'],floor['id'],floor['quadrant']]['collision']==0
            art,symbol=classic_floor_symbol(self,floor,direction)
            for game,tp,tm in aliases(self,dict(tileset=pair,id=mid)):
                key=game,'gen2',tp,tm,None
                if(game,tp,tm)not in self.usage:continue
                note='Purpose-built classic8x8 '+direction+' floor-panel symbol for this clearly identified native spin/stop tile. Crystal has no original counterpart to the Gen3 spinner panel, so the new planar marker uses native GB solid ink and its original palette at1:1, on the complete reviewed room floor. Its contrast pad stays within8x8, each native8px palette has at most4 colors, all floor pixels outside that symbol are exact, and no GBA glyph is resized or traced. Actual source direction/stop, forced movement, warps, collisions, NPCs and all native source map/event data remain unchanged.'
                old=self.rows.get(key)or self.current.get(key)
                if old:row=self.replace_art(old,art,note,symbol)
                else:row=self.row(game,tp,tm,'gen2',art,note)
                row['reverseGen2KantoReview']=dict(symbol,source_signature=MANUAL_SOURCES[pair,mid],source_pair=pair,source_id=mid,source_behavior_hint=expected)
                proof.append(dict(game=game,pair=tp,id=tm,direction=direction,source_signature=MANUAL_SOURCES[pair,mid],floor=floor,symbol_rows=symbol['glyph_rows']))
        (self.out/'new-classic-spin-symbol-evidence.json').write_text(json.dumps(proof,indent=2))

    def cave_ladders(self):
        for(game,pair,mid),usage in self.usage.items():
            key=game,'gen2',pair,mid,None
            if key in self.current or key in self.rows:continue
            src=self.imp.cell_index(game)[pair,mid];spec=LADDERS.get(src['pixel_sha256'])
            if spec is None or src['behavior_hint']!='MB_LADDER':continue
            direction,ice=spec
            ref=self.gb_ref('crystal','ICE_PATH_B1F'if direction=='up'else'ICE_PATH_1F',3 if direction=='up'else 7,3)if ice else self.gb_ref('crystal','UNION_CAVE_1F',7 if direction=='up'else 11,3)
            over=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=src['pixel_sha256']),self.packed,['over'],{'over':src['layer_sha256']['over']})
            if any(p[3]for p in over.get_flattened_data()):
                self.held.append(dict(game=game,pair=pair,id=mid,reason='Ladder needs a complete overhead silhouette review'));continue
            art=self.native(ref,'classic_gen2_complete_'+('ice_'if ice else'cave_')+direction+'_ladder');art['overMask']='0'*256
            row=self.row(game,pair,mid,'gen2',art,
                'Complete native16px '+direction+' ladder reviewed visually in the actual cave family, independently of its warp field. Standing/upward ladders and downward dark-hole ladders use their corresponding actual Crystal graphics; ICE_PATH is separate from ordinary UNION_CAVE. Every original cap, rung, rail and hole-outline pixel stays1:1. No multi-cell stair frame is clipped; native warp destination, movement, collision, actors and events are unchanged.')
            row['reverseGen2KantoReview']=dict(kind='complete_cave_ladder',pixel_scale=1,direction=direction,ice=ice,source_rgba_sha256=src['pixel_sha256'],usage=usage)

    def cave_ladder_heads(self):
        reviewed=[]
        for(pair,mid),ice in LADDER_HEADS.items():
            src=self.checked_native(pair,mid);context=[]
            # The top native16px belongs to a complete standing32px ladder.
            # Validate every map occurrence before replacing the shared atlas.
            for(game,name),(spec,layout)in self.layouts.items():
                if game!='firered'or spec['pair']!=pair:continue
                w,h=layout['width'],layout['height']
                for j,cell in enumerate(layout['mids']):
                    if cell!=mid:continue
                    assert j//w<h-1,(name,j)
                    below=layout['mids'][j+w];other=self.imp.cell_index(game)[pair,below]
                    assert LADDERS.get(other['pixel_sha256'])==('up',ice),(name,mid,below)
                    context.append(dict(map=name,x=j%w,y=j//w,below=below))
            assert context
            ref=self.gb_ref('crystal','ICE_PATH_B1F'if ice else'UNION_CAVE_1F',3 if ice else 7,1)
            for game in GAMES:
                key=game,'gen2',pair,mid,None
                if key in self.current or(game,pair,mid)not in self.usage:continue
                art=self.native(ref,'classic_gen2_complete_standing_ladder_upper_context');art['overMask']='0'*256
                self.rows.pop(key,None)
                row=self.row(game,pair,mid,'gen2',art,
                    'Whole native16x32 standing ladder assembly reviewed in actual cave columns. Every use of this source upper half is checked to sit directly above its matching upward-ladder warp cell; there are no unrelated uses. The complete original Crystal upward ladder is its original lower16px, with the original adjacent rock-bank quadrant above it, retained at1:1. This replaces the native Gen3 cap and rungs together instead of leaving half of a mismatched ladder. Source entrance, warp, collision, ladder direction, scripts and actors are unchanged.')
                row['reverseGen2KantoReview']=dict(kind='complete_standing_ladder_column_upper',pixel_scale=1,source_pair=pair,source_id=mid,source_signature=MANUAL_SOURCES[pair,mid],all_original_occurrences=context,ice=ice)
            reviewed.append(dict(pair=pair,id=mid,ice=ice,source_signature=MANUAL_SOURCES[pair,mid],all_original_occurrences=context))
        (self.out/'complete-ladder-column-evidence.json').write_text(json.dumps(reviewed,indent=2))

    def sandy_shores(self):
        from gb_theme_animation import specification
        water=self.gb_ref('crystal','PALLET_TOWN',29,3);sand=self.gb_ref('crystal','CIANWOOD_CITY',1,0)
        bank=specification(self.cache,water,'water');assert bank;review=[]
        for(game,pair,mid),usage in self.usage.items():
            key=game,'gen2',pair,mid,None
            if key in self.current or key in self.rows:continue
            src=self.imp.cell_index(game)[pair,mid]
            if src['pixel_sha256']not in SAND_SHORES or'WATER'not in(src['behavior_hint']or''):continue
            native=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=src['pixel_sha256']),self.packed)
            over=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=src['pixel_sha256']),self.packed,['over'],{'over':src['layer_sha256']['over']});assert not any(p[3]for p in over.get_flattened_data())
            scores=[]
            for q in range(4):
                blue=warm=0
                for yy in range(q//2*8,q//2*8+8):
                    for xx in range(q%2*8,q%2*8+8):
                        r,g,b,a=native.getpixel((xx,yy))
                        if b-r>12 and b>=g-8:blue+=1
                        elif r-b>18 and g-b>12:warm+=1
                scores.append([blue,warm])
            assert sum(a for a,b in scores)>0 and sum(b for a,b in scores)>0,(pair,mid,scores)
            wet=[a>=b for a,b in scores]
            if not any(wet):wet[max(range(4),key=lambda i:scores[i][0])]=True
            if all(wet):wet[max(range(4),key=lambda i:scores[i][1])]=False
            parts=[dict(donor=water,w=16,h=16,x=0,y=0,srcX=0,srcY=0,animated=True)]
            for q,is_wet in enumerate(wet):
                if not is_wet:parts.append(dict(donor=sand,w=8,h=8,x=q%2*8,y=q//2*8,srcX=q%2*8,srcY=q//2*8))
            art=self.composite(None,parts,'classic_gen2_complete_sandy_shore_8px_grid');art['overMask']='0'*256
            row=self.row(game,pair,mid,'gen2',art,
                'Actual sandy beach/water transition reviewed separately from rock banks, piers, bridge legs and waterfalls. Crystal Cianwood/Route40 use direct walking-ground/water transitions and have no curved sandy-wash graphic. This shore retains original Cianwood beach material and the complete native animated Crystal water frame at1:1; only the sand overlay follows a source-handed coastline mask snapped to the native8px GB grid. Both visible land/water are retained; no rocky ledge replaces sand. Native surf/shallow-water behavior, maps, collision, encounters and events remain unchanged.')
            row.update(animated=True,animation=copy.deepcopy(bank),animationCategory='water');row['compositionPixelHash']=catalog.sha(self.render(row).tobytes())
            row['reverseGen2KantoReview']=dict(kind='sandy_shore_material_adaptation',pixel_scale=1,grid=8,source_rgba_sha256=src['pixel_sha256'],wet_quadrants=wet,native_water_sand_pixels=scores,usage=usage)
            review.append(dict(game=game,pair=pair,id=mid,source_rgba_sha256=src['pixel_sha256'],wet_quadrants=wet,source_material_pixels=scores))
        (self.out/'sandy-shore-evidence.json').write_text(json.dumps(review,indent=2))

    def water_rocks(self):
        from gb_theme_animation import specification
        water=self.gb_ref('crystal','PALLET_TOWN',29,3)
        rock=self.gb_ref('crystal','CHERRYGROVE_CITY',52,0)
        bank=specification(self.cache,water,'water');assert bank
        # Original complete8px coastal boulder, centered at the same four-cell
        # junction. Each source quarter receives exactly one native4px quarter.
        for(game,pair,mid),usage in self.usage.items():
            key=game,'gen2',pair,mid,None
            if key in self.current or key in self.rows:continue
            src=self.imp.cell_index(game)[pair,mid];q=WATER_ROCKS.get(src['pixel_sha256'])
            if q is None or 'WATER'not in (src['behavior_hint']or''):continue
            source=dict(game=game,tileset=pair,id=mid,hash=src['pixel_sha256'])
            over=preview.native_donor(self.cache,source,self.packed,['over'],{'over':src['layer_sha256']['over']})
            assert not any(p[3]for p in over.get_flattened_data())
            parts=[dict(donor=water,w=16,h=16,x=0,y=0,srcX=0,srcY=0,animated=True),
                   dict(donor=rock,w=4,h=4,x=12 if q%2==0 else 0,y=12 if q//2==0 else 0,srcX=q%2*4,srcY=q//2*4)]
            art=self.composite(None,parts,'classic_gen2_complete_coastal_small_rock_quarter_'+str(q));art['overMask']='0'*256
            row=self.row(game,pair,mid,'gen2',art,
                'Whole four-cell water-rock junction reviewed in the native ocean/current families. The complete original Crystal8x8 coastal boulder is retained at1:1, centered on the same source junction and split into its four exact4x4 quarters; no rock is resized or clipped. The rest of each16px tile uses fingerprinted native animated Crystal water. Each source surf/current behavior, map, collision, encounter and script is unchanged.')
            row.update(animated=True,animation=copy.deepcopy(bank),animationCategory='water')
            row['compositionPixelHash']=catalog.sha(self.render(row).tobytes())
            row['reverseGen2KantoReview']=dict(kind='complete_coastal_boulder_quarter',pixel_scale=1,
                native_boulder_dimensions=[8,8],boulder_quadrant=q,source_rgba_sha256=src['pixel_sha256'],usage=usage)
        # Prove the four reviewed slices reconstruct every original boulder pixel.
        original=self.gb_image(rock).crop((0,0,8,8));rebuilt=Image.new('RGBA',(8,8))
        for q in range(4):rebuilt.paste(original.crop((q%2*4,q//2*4,q%2*4+4,q//2*4+4)),(q%2*4,q//2*4))
        assert rebuilt.tobytes()==original.tobytes()
        original.resize((256,256),Image.Resampling.NEAREST).save(self.out/'complete-native-coastal-boulder.png')

    def pure_water(self):
        ref=self.gb_ref('crystal','PALLET_TOWN',29,3)
        ts=self.imp.table('crystal','tilesets')[ref['tileset']]
        block=catalog.lua_array(catalog.dict_at(ts['blocks'],ref['id']+1))
        assert [block[10],block[11],block[14],block[15]]==[20]*4
        approved=set(PURE_WATER_HASHES)
        for(game,pair,mid),usage in self.usage.items():
            key=game,'gen2',pair,mid,None
            if key in self.current or key in self.rows:continue
            src=self.imp.cell_index(game)[pair,mid]
            if src['pixel_sha256']not in approved:continue
            if 'WATER'not in (src['behavior_hint']or''):continue
            source=dict(game=game,tileset=pair,id=mid,hash=src['pixel_sha256'])
            overhead=preview.native_donor(self.cache,source,self.packed,['over'],{'over':src['layer_sha256']['over']})
            assert not any(p[3]for p in overhead.get_flattened_data()),(pair,mid)
            art=self.native(ref,'classic_gen2_complete_animated_water_surface');art['overMask']='0'*256
            row=self.row(game,pair,mid,'gen2',art,
                'Complete native water surface reviewed at source resolution in the entire FR/LG pair inventory. This is water only: no coastline, beach, rocks, bridge/ship/piers, posts or waterfall pixels are discarded. The full native Crystal water quadrant is retained at1:1 and uses its fingerprinted native animation bank. Source ocean/pond/current behavior, movement, maps, events and scripts remain unchanged.')
            row['reverseGen2KantoReview']=dict(kind='reviewed_complete_water_surface',pixel_scale=1,
                source_rgba_sha256=src['pixel_sha256'],original_crystal_rgba_sha256=catalog.sha(self.gb_image(ref).tobytes()),
                native_over_pixels=0,usage=usage)

    def replace_art(self,row,art,note,proof):
        # Shared water normalizer preserves every visible nonwater pixel and
        # records exact prior-key supersessions without editing old modules.
        from reverse_gen2_hoenn_outdoor_finish import Review
        return Review.replace_art(self,row,art,note,proof)

    def coherent_water_policy(self):
        from reverse_gen2_hoenn_outdoor_finish import Review
        Review.coherent_cave_water(self,lambda pair,mid:True)
        (self.out/'coherent-water-policy-evidence.json').write_text(json.dumps(self.proofs,indent=2))

    def native_floor_donor_audit(self):
        audited=[];kinds=('reviewed_complete_material','complete_room_material','complete_contextual_floor_or_ground','complete_clinic_staff_floor','exact_complete_forward_cell')
        for row in self.rows.values():
            proof=row.get('reverseGen2KantoReview',{});ref=row.get('donor')
            if proof.get('kind')not in kinds or ref is None or not plain_floor(row['role']):continue
            native=self.imp.cell_index('crystal')[ref['tileset'],ref['id'],ref['quadrant']]
            assert native['collision']!=7,('A solid native GSC wall/object was mislabeled as plain floor',identity(row),ref)
            audited.append(dict(game=row['game'],pair=row['tileset'],id=row['id'],role=row['role'],native_floor_ref=ref,native_collision=native['collision'],native_category=native['behavior_hint']))
        (self.out/'native-floor-donor-category-audit.json').write_text(json.dumps(audited,indent=2))

    def previews(self):
        scenes=('FR_PLAYERS_HOUSE_1F','FR_CERULEAN_CITY_MART','FR_VERMILION_CITY_POKEMON_CENTER_1F',
                'FR_CELADON_CITY_GAME_CORNER','FR_CELADON_CITY_DEPARTMENT_STORE_2F','FR_OAKS_LAB',
                'FR_SAFFRON_CITY_GYM','FR_ROCKET_HIDEOUT_B1F','FR_ROCKET_HIDEOUT_B2F','FR_VIRIDIAN_CITY_GYM','FR_VIRIDIAN_FOREST','FR_SAFARI_ZONE_CENTER','FR_SILPH_CO_1F','FR_POKEMON_MANSION_1F','FR_MT_MOON_1F','FR_FOUR_ISLAND_ICEFALL_CAVE_1F','FR_ROUTE_1','FR_VIRIDIAN_CITY')
        for name in scenes:
            if('firered',name)not in self.layouts:continue
            spec,layout=self.layouts['firered',name];w,h=layout['width'],layout['height']
            before=Image.new('RGBA',(w*16,h*16));current=before.copy();after=before.copy();images={}
            for i,mid in enumerate(layout['mids']):
                key='firered','gen2',spec['pair'],mid,None
                if mid not in images:
                    src=self.imp.cell_index('firered')[spec['pair'],mid]
                    original=preview.native_donor(self.cache,dict(game='firered',tileset=spec['pair'],id=mid,hash=src['pixel_sha256']),self.packed)
                    old=self.current.get(key);new=self.rows.get(key)
                    images[mid]=original,self.render(old)if old else original,self.render(new or old)if new or old else original
                for canvas,image in zip((before,current,after),images[mid]):canvas.paste(image,((i%w)*16,(i//w)*16))
            for label,im in zip(('before','current','staged'),(before,current,after)):im.save(self.out/(name+'-'+label+'.png'))
            scale=2;canvas=Image.new('RGB',(w*16*6+48,h*32+48),'#18212b');draw=ImageDraw.Draw(canvas)
            font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
            for n,(label,im)in enumerate(zip(('Original FireRed','Existing Crystal theme','New reviewed counterparts'),(before,current,after))):
                x=8+n*(w*32+16);draw.text((x,6),label,font=font,fill='white');canvas.paste(im.resize((w*32,h*32),Image.Resampling.NEAREST),(x,32))
            canvas.save(self.out/(name+'-comparison.png'))

    def missing_contacts(self):
        groups=defaultdict(list)
        for(game,pair,mid),usage in self.usage.items():
            if game!='firered'or(game,'gen2',pair,mid,None)in self.current or(game,'gen2',pair,mid,None)in self.rows:continue
            src=self.imp.cell_index(game)[pair,mid]
            category='water'if'WATER'in src['behavior_hint']else'cave'if src['behavior_hint']=='MB_CAVE'else'other'
            groups[category,src['pixel_sha256']].append(dict(pair=pair,id=mid,behavior=src['behavior_hint'],
                count=sum(v['count']for v in usage),map=usage[0]['map']))
        for category in('water','cave','other'):
            values=[v for(k,_),v in groups.items()if k==category]
            values.sort(key=lambda items:-sum(v['count']for v in items))
            if category=='other':values=values[:96]
            index=[];font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
            for offset in range(0,len(values),18):
                canvas=Image.new('RGB',(1500,18*90),'#18212b');draw=ImageDraw.Draw(canvas)
                for n,items in enumerate(values[offset:offset+18]):
                    item=items[0];rec=self.imp.cell_index('firered')[item['pair'],item['id']]
                    im=preview.native_donor(self.cache,dict(game='firered',tileset=item['pair'],id=item['id'],hash=rec['pixel_sha256']),self.packed)
                    y=n*90;canvas.paste(im.resize((80,80),Image.Resampling.NEAREST),(4,y+4))
                    draw.text((96,y+3),str(offset+n)+' '+item['pair']+' / '+str(item['id'])+' '+item['behavior']+' '+item['map'],font=font,fill='white')
                    draw.text((96,y+27),'instances='+str(sum(i['count']for i in items))+' aliases='+str(len(items)),font=font,fill='white')
                    index.append(dict(number=offset+n,source_hash=rec['pixel_sha256'],targets=items))
                canvas.save(self.out/(category+'-missing-'+str(offset//18+1).zfill(2)+'.png'))
            (self.out/(category+'-missing.json')).write_text(json.dumps(index,indent=2))
            for start in range(0,len(index),60):
                canvas=Image.new('RGB',(1200,10*132),'#18212b');draw=ImageDraw.Draw(canvas)
                for n,item in enumerate(index[start:start+60]):
                    target=item['targets'][0];rec=self.imp.cell_index('firered')[target['pair'],target['id']]
                    im=preview.native_donor(self.cache,dict(game='firered',tileset=target['pair'],id=target['id'],hash=rec['pixel_sha256']),self.packed)
                    x,y=n%6*200,n//6*132;canvas.paste(im.resize((80,80),Image.Resampling.NEAREST),(x+4,y+3))
                    draw.text((x+90,y+5),str(item['number'])+' / '+str(target['id']),font=font,fill='white')
                    draw.text((x+4,y+86),target['behavior'][3:][:25],font=font,fill='white')
                    draw.text((x+4,y+105),target['pair'][-24:],font=font,fill='#c5d0da')
                canvas.save(self.out/(category+'-grid-'+str(start//60+1).zfill(2)+'.png'))

    def contacts(self,clear=False):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
        values=[(i,c)for i,c in enumerate(self.candidates)if not clear or not c['ambiguous']and not c['unsafe']]
        for offset in range(0,len(values),12):
            canvas=Image.new('RGB',(1500,12*102),'#18212b');draw=ImageDraw.Draw(canvas)
            for local,(number,c) in enumerate(values[offset:offset+12]):
                y=local*102;game,pair,mid=c['targets'][0];rec=self.imp.cell_index(game)[pair,mid]
                native=preview.native_donor(self.cache,dict(game=game,tileset=pair,id=mid,hash=rec['pixel_sha256']),self.packed)
                gb=self.gb_image(c['ref'])
                for col,im in enumerate((native,gb)):canvas.paste(im.resize((80,80),Image.Resampling.NEAREST),(4+col*90,y+18))
                draw.text((194,y+2),str(number)+' '+pair+' / '+str(mid)+' — '+c['ref']['map'],font=font,fill='white')
                draw.text((194,y+24),','.join(c['roles'])[:180],font=font,fill='white')
                draw.text((194,y+45),'AMBIGUOUS='+str(c['ambiguous'])+' / FOOTPRINT REVIEW='+str(c['unsafe'])+' / target aliases='+str(len(c['targets'])),font=font,fill='#c5d0da')
            canvas.save(self.out/(('clear-'if clear else'candidates-')+str(offset//12+1).zfill(2)+'.png'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--contacts',action='store_true');p.add_argument('--clear-contacts',action='store_true');p.add_argument('--missing-contacts',action='store_true');p.add_argument('--stage',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--activate',action='store_true');args=p.parse_args()
    review=Finish();inventory=review.inventory();candidates=review.forward_candidates()
    if args.contacts:review.contacts()
    if args.clear_contacts:review.contacts(True)
    result=dict(inventory=inventory['games'],candidate_groups=len(candidates),unambiguous=sum(not c['ambiguous']and not c['unsafe']for c in candidates))
    if args.stage or args.validate or args.activate:
        rows=review.stage();review.previews()
        if args.validate or args.activate:result['proof']=review.validate()
        assert not args.activate or args.validate
        review.write(TARGET if args.activate else review.out/'candidate.lua')
        covered=sum(m['covered']for m in review.maps)+sum(sum(u['count']for u in review.usage[r['game'],r['tileset'],r['id']])for r in rows if identity(r)not in review.current)
        result.update(new_rows=len(rows),covered=covered,remaining=sum(m['cells']for m in review.maps)-covered,held=len(review.held))
        (review.out/'stage-summary.json').write_text(json.dumps(result,indent=2))
    if args.missing_contacts:review.missing_contacts()
    print(json.dumps(result))


if __name__=='__main__':main()
