"""Continue reviewed Crystal counterparts for actual Hoenn outdoor source cells.

This separate author writes only private candidates. Every binding uses actual
logical native-layout usage, complete original GB pixels and guarded per-game
source identities; map data, events and the active modules remain unchanged.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import catalog
import preview
from reverse_common import ReverseReview, ROOT
from reverse_hoenn_review import native_geometry, ground_ref
from reverse_gen2_hoenn_outdoor_finish import Review as PreviousReview, scope, identity, digest, GAMES
from johto_remaining_review import artwork
from reverse_kanto_review import runs
from reverse_kanto_review import exterior
from reverse_oldale_review import native_piece, mask_piece
from gb_theme_animation import specification, foreground_frames

TARGET = ROOT / 'mappings/reverse_gen2_hoenn_outdoor_complete.lua'


# Frozen actual source geometry, behavior and all-cartridge RGBA bindings.
PETALBURG_BINDINGS = {'79c5ef62964ed9aa746deaba88fa2643195313c5b1651eb5410bd78461946f82': {'family': 'primary', 'mid': 508, 'source_sha256': {'emerald/general__battle_frontier_outside_east': 'd8f9826df54fbb48f64ede7f3090a985ec68b39eba56a5af5069797ef7ca4ca8', 'emerald/general__battle_frontier_outside_west': 'd8f9826df54fbb48f64ede7f3090a985ec68b39eba56a5af5069797ef7ca4ca8', 'emerald/general__lilycove': 'd8f9826df54fbb48f64ede7f3090a985ec68b39eba56a5af5069797ef7ca4ca8', 'emerald/general__petalburg': 'd8f9826df54fbb48f64ede7f3090a985ec68b39eba56a5af5069797ef7ca4ca8'}}, 'ef2d6f0f5e3fec85a80bdf63bcad5bdf17cc6283e6f88ea999ceec793d372d41': {'family': 'primary', 'mid': 509, 'source_sha256': {'emerald/general__battle_frontier_outside_east': 'e1a04db155c16d14dab3dbdee666de95b747b59577decc97a1eacbff2ae533f5', 'emerald/general__battle_frontier_outside_west': 'e1a04db155c16d14dab3dbdee666de95b747b59577decc97a1eacbff2ae533f5', 'emerald/general__lilycove': 'e1a04db155c16d14dab3dbdee666de95b747b59577decc97a1eacbff2ae533f5', 'emerald/general__petalburg': 'e1a04db155c16d14dab3dbdee666de95b747b59577decc97a1eacbff2ae533f5'}}, '893481509ab7668649f93abc2d5028dbd0481ed86f7acfca38f7845e16db4c47': {'family': 'primary', 'mid': 508, 'source_sha256': {'ruby/general__lilycove': '4089cd03667976c5045e1713fe5d863fa9b406d8861a38e41b27177b7202745f', 'ruby/general__petalburg': '4089cd03667976c5045e1713fe5d863fa9b406d8861a38e41b27177b7202745f', 'sapphire/general__lilycove': '4089cd03667976c5045e1713fe5d863fa9b406d8861a38e41b27177b7202745f', 'sapphire/general__petalburg': '4089cd03667976c5045e1713fe5d863fa9b406d8861a38e41b27177b7202745f'}}, '1e053a8daf32792891e96f748196bdc35305dfbc2d493575719e6e9c071d1f03': {'family': 'primary', 'mid': 509, 'source_sha256': {'ruby/general__lilycove': '193d979a59c7e15860c93b1c4d3e21d5d35a6634c0e147a75897d8bf2745b1b1', 'ruby/general__petalburg': '193d979a59c7e15860c93b1c4d3e21d5d35a6634c0e147a75897d8bf2745b1b1', 'sapphire/general__lilycove': '193d979a59c7e15860c93b1c4d3e21d5d35a6634c0e147a75897d8bf2745b1b1', 'sapphire/general__petalburg': '193d979a59c7e15860c93b1c4d3e21d5d35a6634c0e147a75897d8bf2745b1b1'}}, 'fa61d583643175a7a1565c7be445f917b01d34eb333cc96318c428a4a996c04d': {'family': 'primary', 'mid': 304, 'source_sha256': {'ruby/general__mauville': 'c2ef3bddfcc353a3ca5987f4d12a257eb8fa091507f5b8821885a1268c8a1241', 'ruby/general__mossdeep': 'c2ef3bddfcc353a3ca5987f4d12a257eb8fa091507f5b8821885a1268c8a1241', 'ruby/general__petalburg': 'c2ef3bddfcc353a3ca5987f4d12a257eb8fa091507f5b8821885a1268c8a1241', 'ruby/general__sootopolis': 'c2ef3bddfcc353a3ca5987f4d12a257eb8fa091507f5b8821885a1268c8a1241', 'sapphire/general__mauville': 'c2ef3bddfcc353a3ca5987f4d12a257eb8fa091507f5b8821885a1268c8a1241', 'sapphire/general__mossdeep': 'c2ef3bddfcc353a3ca5987f4d12a257eb8fa091507f5b8821885a1268c8a1241', 'sapphire/general__petalburg': 'c2ef3bddfcc353a3ca5987f4d12a257eb8fa091507f5b8821885a1268c8a1241', 'sapphire/general__sootopolis': 'c2ef3bddfcc353a3ca5987f4d12a257eb8fa091507f5b8821885a1268c8a1241'}}, '0b7e343ad7b391916757480327fff3387dd4af7ef6e213ddf847c1d3137daccd': {'family': 'primary', 'mid': 305, 'source_sha256': {'ruby/general__mauville': '6e981bcc65ecdb4b25de5640b6e2c8f61ed7bb1a48c4425ca37542f337403892', 'ruby/general__mossdeep': '6e981bcc65ecdb4b25de5640b6e2c8f61ed7bb1a48c4425ca37542f337403892', 'ruby/general__petalburg': '6e981bcc65ecdb4b25de5640b6e2c8f61ed7bb1a48c4425ca37542f337403892', 'ruby/general__sootopolis': '6e981bcc65ecdb4b25de5640b6e2c8f61ed7bb1a48c4425ca37542f337403892', 'sapphire/general__mauville': '6e981bcc65ecdb4b25de5640b6e2c8f61ed7bb1a48c4425ca37542f337403892', 'sapphire/general__mossdeep': '6e981bcc65ecdb4b25de5640b6e2c8f61ed7bb1a48c4425ca37542f337403892', 'sapphire/general__petalburg': '6e981bcc65ecdb4b25de5640b6e2c8f61ed7bb1a48c4425ca37542f337403892', 'sapphire/general__sootopolis': '6e981bcc65ecdb4b25de5640b6e2c8f61ed7bb1a48c4425ca37542f337403892'}}, '787b7575a21e6628634e2c8b988eaa698de8ff131a12af7d1e15eb8a0a5b001c': {'family': 'general__petalburg', 'mid': 590, 'source_sha256': {'ruby/general__petalburg': 'daca7b01d143ffd2ea0db2f668c5f545461eaa0329f84708b1626ac596bf89b4', 'sapphire/general__petalburg': 'daca7b01d143ffd2ea0db2f668c5f545461eaa0329f84708b1626ac596bf89b4'}}, '12588d15df0ad270d1f10994294b14f0a56672272ad946bbbf21fd4004874ce7': {'family': 'general__petalburg', 'mid': 589, 'source_sha256': {'ruby/general__petalburg': 'e06fcb10e88b9d4c3c31fa99bbd6225cac5da62eb0c4f6f52f36097f924eb15d', 'sapphire/general__petalburg': 'e06fcb10e88b9d4c3c31fa99bbd6225cac5da62eb0c4f6f52f36097f924eb15d'}}, '20db3ea921862318360d5fc7202532aaa97e2bd650a6f575c7b5723338a24f86': {'family': 'primary', 'mid': 304, 'source_sha256': {'emerald/general__mauville': 'b8687516b11e0e7f271d0ccedc253cdc7adff357644a1eae22501faf3539883e', 'emerald/general__mossdeep': 'b8687516b11e0e7f271d0ccedc253cdc7adff357644a1eae22501faf3539883e', 'emerald/general__petalburg': 'b8687516b11e0e7f271d0ccedc253cdc7adff357644a1eae22501faf3539883e', 'emerald/general__sootopolis': 'b8687516b11e0e7f271d0ccedc253cdc7adff357644a1eae22501faf3539883e'}}, '60fe8c2207d3267f761843e973bdd9bcf836790c5c532920268aa354d665e0a5': {'family': 'primary', 'mid': 305, 'source_sha256': {'emerald/general__mauville': '3c800ed5039e83c60cfc41ec506343f76014bd3c2cc9e530d5f696e469a557aa', 'emerald/general__mossdeep': '3c800ed5039e83c60cfc41ec506343f76014bd3c2cc9e530d5f696e469a557aa', 'emerald/general__petalburg': '3c800ed5039e83c60cfc41ec506343f76014bd3c2cc9e530d5f696e469a557aa', 'emerald/general__sootopolis': '3c800ed5039e83c60cfc41ec506343f76014bd3c2cc9e530d5f696e469a557aa'}}, 'accb80d17286ad46c4d71690aafaad1f81f862eb709d99b087f2ff96689aed3b': {'family': 'general__petalburg', 'mid': 590, 'source_sha256': {'emerald/general__petalburg': 'e9433e3703433aec85a91a6034c3de4aafff5ae22c6b707e0ae51cafa4a0572b'}}, 'a969c3aeabbc01e54539fd6aa3736cb83ad3fc4ed2f1ade380336341491c0839': {'family': 'general__petalburg', 'mid': 589, 'source_sha256': {'emerald/general__petalburg': 'b1c02b61f854e4c068b6d9f754f4d764db322fc4afe266c4287b478ddf6d445f'}}, 'e58e866c0835e68abfdf91ee5f54eb509864098f7a47b6753bb4058f128e515b': {'family': 'general__petalburg', 'mid': 592, 'source_sha256': {'ruby/general__petalburg': '9e6ba1f7f03d21f7568a546cdb340ac83d08686796914f35517ced91f59c7315', 'sapphire/general__petalburg': '9e6ba1f7f03d21f7568a546cdb340ac83d08686796914f35517ced91f59c7315'}}, '4a87f71cb2df514634e162ea678036782ae3daada20c02dc4e7b957f223baf7f': {'family': 'general__petalburg', 'mid': 593, 'source_sha256': {'ruby/general__petalburg': '95184a455479cab0e705c83ca647af42fbb0a17474d37503e96bebcf25554be3', 'sapphire/general__petalburg': '95184a455479cab0e705c83ca647af42fbb0a17474d37503e96bebcf25554be3'}}, 'd3217783ee39b66fc6346bfee6624c68a8fb4aac5ae05111883190e9a6e9bb73': {'family': 'general__petalburg', 'mid': 594, 'source_sha256': {'ruby/general__petalburg': 'c5289de9597af15a800b7484f0f502a51a249f62a87eb09ec7db3df10258e56c', 'sapphire/general__petalburg': 'c5289de9597af15a800b7484f0f502a51a249f62a87eb09ec7db3df10258e56c'}}, 'ce4e655ea673f2703de5472953f87013a251be3dd01cc63c3b3e0d913d78acf1': {'family': 'general__petalburg', 'mid': 595, 'source_sha256': {'ruby/general__petalburg': '5dc9fd60ebb4af7be6c1975129b3d02e6a5d6766a16b6b32c7c459951f8da6d9', 'sapphire/general__petalburg': '5dc9fd60ebb4af7be6c1975129b3d02e6a5d6766a16b6b32c7c459951f8da6d9'}}, '4a8b7052e4ca4f70fef2585099cd604c50559b8d5435b3583f9cd412e59f1bea': {'family': 'general__petalburg', 'mid': 597, 'source_sha256': {'ruby/general__petalburg': 'caef262521c8e958a100d4460f9aef83140b92cc7c4756069c1d85e347b1d98f', 'sapphire/general__petalburg': 'caef262521c8e958a100d4460f9aef83140b92cc7c4756069c1d85e347b1d98f'}}, 'a9a4026dc125c8fa01475c2a3baa4e5a907cad78c216f2c6ba12af2ba7505c57': {'family': 'general__petalburg', 'mid': 598, 'source_sha256': {'ruby/general__petalburg': 'e338fdfdca1a55d143a28c53536526806216708adb4451648ebecd9c8a75fe0a', 'sapphire/general__petalburg': 'e338fdfdca1a55d143a28c53536526806216708adb4451648ebecd9c8a75fe0a'}}, '9a253baec2d98f6e7adc6b6b1f8a2201480f140c20124c018a39a9c47de59a97': {'family': 'general__petalburg', 'mid': 600, 'source_sha256': {'ruby/general__petalburg': 'fbdc9dc0f13adca87c0cfb9c036fe78f8f9fc871153a4d7dfa78f42cb8cccdb0', 'sapphire/general__petalburg': 'fbdc9dc0f13adca87c0cfb9c036fe78f8f9fc871153a4d7dfa78f42cb8cccdb0'}}, '3a66ba3058213e195cdb7a940e3e49a7079d2fda859e9ef6f4dcd38cb4144e36': {'family': 'general__petalburg', 'mid': 601, 'source_sha256': {'ruby/general__petalburg': '544e423868d323dedef53d718ce894981fef3dca714bffe04974c65b1a53c3b5', 'sapphire/general__petalburg': '544e423868d323dedef53d718ce894981fef3dca714bffe04974c65b1a53c3b5'}}, '56066e5335576b6dfafbc187b28cab8f2447c6b540afc34e3092c17434bedf03': {'family': 'general__petalburg', 'mid': 592, 'source_sha256': {'emerald/general__petalburg': '7c5ec4f1e91d28ec6727737aeb83a841609e83b9b2e82959deee4293cda75676'}}, 'b35db115fe1f1f67e2f4ffb62055382d010cfe92d28bbb90e6e7b87c6f589b5c': {'family': 'general__petalburg', 'mid': 593, 'source_sha256': {'emerald/general__petalburg': '95184a455479cab0e705c83ca647af42fbb0a17474d37503e96bebcf25554be3'}}, '76a75a3876890128c8491570d1f1c72b9176ef964aea201bd89ae2baccb89cc5': {'family': 'general__petalburg', 'mid': 594, 'source_sha256': {'emerald/general__petalburg': 'b129df3d26312aec2c195f36f994f0e19ef74decbf08e836f98b6b97eda4e267'}}, 'd283611f836002ff16459b95d30196f47c2de277dd278d678c9b25ffc66e5841': {'family': 'general__petalburg', 'mid': 595, 'source_sha256': {'emerald/general__petalburg': '0ad8b7d5114bc6c72b25334665f8e294795c4122fa9f2f27c4950af2b9669f5b'}}, '802eb1ac4cc822310bf2dce4086da9a77d151b461bde4c943ac25c5f27821066': {'family': 'general__petalburg', 'mid': 597, 'source_sha256': {'emerald/general__petalburg': '103214c0a3a9d35d6fe94a046c2eaddd9a14d18bb0afdc13a8ae5fcf979bffc0'}}, '5315eb405a77c308112d5c578084dcf0fb771f6db05c0c1eac78b89c253b77b6': {'family': 'general__petalburg', 'mid': 598, 'source_sha256': {'emerald/general__petalburg': '2219b930befa45831a1481ed1a0b33fa5de0d3978d6bc0a75deddad1f6fa1730'}}, 'ff92a7e03966d167637578b048a157e787ca4dfd085ffce98d5706b9a3ca4660': {'family': 'general__petalburg', 'mid': 600, 'source_sha256': {'emerald/general__petalburg': 'a0552f2c648dde19eb7befb4d2e8df4314f642a7c349d322f3108d2b5e7139bc'}}, 'b06385734b1a697bcdd2c9bacb7de3e58d8a71942cd92fe80d5d926cffe842a4': {'family': 'general__petalburg', 'mid': 601, 'source_sha256': {'emerald/general__petalburg': '7f86af5107c810d9f958a9d6efd82eb4a09047f9f784db44d81e6b3e02db7ff4'}}}

CORE_CAVE_BINDINGS = {'1fe58c9f4c6e30ea450f5ed103f00e516fa57b5ba9c8c24ebc783516d08e2b1a': {'family': 'general__sootopolis', 'mid': 729, 'source_sha256': {'ruby/general__sootopolis': '7f79b411e84b03cac0c0d6e7111a2eb389fc43708a9982dc9ac6160641e7bbde', 'sapphire/general__sootopolis': '7f79b411e84b03cac0c0d6e7111a2eb389fc43708a9982dc9ac6160641e7bbde', 'emerald/general__sootopolis': '7f79b411e84b03cac0c0d6e7111a2eb389fc43708a9982dc9ac6160641e7bbde'}}, '055a4972dbc4ec6a1d979d414c444e7d0bb9e039b200892ea5528d3a2cd8a93d': {'family': 'general__rusturf_tunnel', 'mid': 529, 'source_sha256': {'ruby/general__rusturf_tunnel': '8ef42780765199280e86610b1baeb3ddc4c0e923e0f53281636adedd3ff73f4f', 'sapphire/general__rusturf_tunnel': '8ef42780765199280e86610b1baeb3ddc4c0e923e0f53281636adedd3ff73f4f'}}, '203ff266b72f48cbb8ff34527fba3172d56a307a879445a4410a73f039f6d105': {'family': 'general__rusturf_tunnel', 'mid': 513, 'source_sha256': {'ruby/general__rusturf_tunnel': '57c44bbf3227f85c049d1a969047972f2d4c302accea6363dcd718bad334e87f', 'sapphire/general__rusturf_tunnel': '57c44bbf3227f85c049d1a969047972f2d4c302accea6363dcd718bad334e87f'}}, '5a2e3854ff0b0e9cbb9c4c0ad0ded223f9594c8ebb8fe0fc19a5d8fe82b5243a': {'family': 'general__rusturf_tunnel', 'mid': 529, 'source_sha256': {'emerald/general__rusturf_tunnel': 'cb2cd0236f357d2a1e9dc3c7fdd8c48e9761d2ffcce1124fc524e65d78b91306'}}, '0199df047377b075964703790b906a8bed45c59425e6494728bc7c91c9ed19a6': {'family': 'general__rusturf_tunnel', 'mid': 521, 'source_sha256': {'ruby/general__rusturf_tunnel': '13ada6b1ff259a3ca698a092fee683535253bb7624868ab46e12d2889c3dbccf', 'sapphire/general__rusturf_tunnel': '13ada6b1ff259a3ca698a092fee683535253bb7624868ab46e12d2889c3dbccf'}}, 'ac385b21afd9ecdfb882977da474d022be67864458e8c8a917443d600e75535b': {'family': 'general__rusturf_tunnel', 'mid': 537, 'source_sha256': {'ruby/general__rusturf_tunnel': '966c54177a6d91593802c15da8026612976a50ac0ad25c79e20463d82c178a1a', 'sapphire/general__rusturf_tunnel': '966c54177a6d91593802c15da8026612976a50ac0ad25c79e20463d82c178a1a'}}, 'a957f1b447a3220fd16c8a2870a768c4d92fa8d086b0944b35e9d849ea34f992': {'family': 'general__rusturf_tunnel', 'mid': 513, 'source_sha256': {'emerald/general__rusturf_tunnel': '092da938825ed8aeda1f741dc28eee83c4c693b92edd8aeba559d796370919c7'}}, '0a721668e0ca857757386eb560009595766033221a8899b20f3954f395b71856': {'family': 'general__rusturf_tunnel', 'mid': 528, 'source_sha256': {'ruby/general__rusturf_tunnel': '991a7b6e1d8b9ea110e7afe299528e4d67e3c6b906104a98142345c3e34a6777', 'sapphire/general__rusturf_tunnel': '991a7b6e1d8b9ea110e7afe299528e4d67e3c6b906104a98142345c3e34a6777'}}, '9b57ff62f4fb8d7b280bbf3f0e43cb0303a167168fcb45c85cd88e73a18f5743': {'family': 'general__rusturf_tunnel', 'mid': 530, 'source_sha256': {'ruby/general__rusturf_tunnel': '1e5940fa25aab542b0b056ba35714517eba30943d9d67ba173ede643a2a0f0b6', 'sapphire/general__rusturf_tunnel': '1e5940fa25aab542b0b056ba35714517eba30943d9d67ba173ede643a2a0f0b6'}}, 'aab490b92c1ee111607f735a3670cbdcbe5a50de6904b3ff9c2da58dca3d26a0': {'family': 'general__rusturf_tunnel', 'mid': 521, 'source_sha256': {'emerald/general__rusturf_tunnel': '878d53d466e52c0bf1d830b5f63ba53f54efec9a3c3efe408381a0952db5fd7a'}}, 'aa20f6aad8d97adc26c8c1ba6f5bf2195dd689010684caddc0c0eafc2fa53060': {'family': 'general__rusturf_tunnel', 'mid': 537, 'source_sha256': {'emerald/general__rusturf_tunnel': '0bd23c9eb0ceeead90aa44eaa63b234938a9755d2a1b9441f8bfa19f97bec1d8'}}, 'bd7faffcc636736ce7a0d773e6a0d90b6f805557363e9059291537bccec86677': {'family': 'general__rusturf_tunnel', 'mid': 514, 'source_sha256': {'ruby/general__rusturf_tunnel': '3929bceb7f93bd5349a9604f781c6354aa97bf8b3b7002f7b366b10a4fcb08a6', 'sapphire/general__rusturf_tunnel': '3929bceb7f93bd5349a9604f781c6354aa97bf8b3b7002f7b366b10a4fcb08a6'}}, '1426757685c1e3daf347a675d3927b340c11b57e3418145ab2ef8693f9819da3': {'family': 'general__rusturf_tunnel', 'mid': 528, 'source_sha256': {'emerald/general__rusturf_tunnel': '972206be4883da17606d7dbff363d44b672ee267eadee11db6d98a3c2b270fa3'}}, 'efad68ea9ef76b74f63fabac1a31bcfe40fd97e7b59049a21b54d5fd77f6b1a0': {'family': 'general__rusturf_tunnel', 'mid': 530, 'source_sha256': {'emerald/general__rusturf_tunnel': 'fb4872e9bfc23b90ad212a69c88a7ff170799b8f708c056909fe68a372d59b8e'}}, '4d9194a294739be5536852222c6a98e6822abe5ed2511fd11350fbddf72cc1b9': {'family': 'general__rusturf_tunnel', 'mid': 517, 'source_sha256': {'ruby/general__rusturf_tunnel': 'c655db198fad884afca4c28670a42d4dc5d3d28c871e19fd45bb15f22c1aaa34', 'sapphire/general__rusturf_tunnel': 'c655db198fad884afca4c28670a42d4dc5d3d28c871e19fd45bb15f22c1aaa34'}}, '1c92ab1b06b62d71847a70b5eae2b40efaee9d14880eb8ee83b1581f7bc8526c': {'family': 'general__rusturf_tunnel', 'mid': 539, 'source_sha256': {'ruby/general__rusturf_tunnel': '51ac89ed7080116fc34d2f1534c4db910c32caf80dddf942ee5fd5c62fcb6bde', 'sapphire/general__rusturf_tunnel': '51ac89ed7080116fc34d2f1534c4db910c32caf80dddf942ee5fd5c62fcb6bde'}}, '0bf226c7532eca773870a8d208f2a6a336728f1cf4a6a2f2d75e0a66c7d265d0': {'family': 'general__rusturf_tunnel', 'mid': 514, 'source_sha256': {'emerald/general__rusturf_tunnel': '5a4756afbf167eb10b4ada4b1bccf8f2520a61e974193739903fa3de863a8541'}}, '0f80f95e5ef0b2b44e02b055b431b320647cf5901626b5866dadd6506576fb42': {'family': 'general__rusturf_tunnel', 'mid': 518, 'source_sha256': {'ruby/general__rusturf_tunnel': '1140abe343c807f2c57b68548fcb401de01bac65a2dca96d83583e03ff972fd9', 'sapphire/general__rusturf_tunnel': '1140abe343c807f2c57b68548fcb401de01bac65a2dca96d83583e03ff972fd9'}}, '2f5616f3847a1988c80d54caf2f53f37642e35b36cbf4cc00eb385b95d36049a': {'family': 'general__rusturf_tunnel', 'mid': 538, 'source_sha256': {'ruby/general__rusturf_tunnel': '33e642eb1b40ea9d24e346aed837762ea1bcb013fa76d72d30898314acb65d5d', 'sapphire/general__rusturf_tunnel': '33e642eb1b40ea9d24e346aed837762ea1bcb013fa76d72d30898314acb65d5d'}}, 'e7af90bd6ee626fb938d9af42ddaa9d236d2810de5aeafd7dee149243a7e15d2': {'family': 'general__rusturf_tunnel', 'mid': 515, 'source_sha256': {'ruby/general__rusturf_tunnel': 'd3bbc128786e4415876bbe31f20b0ff35f3170d99575b966bf882b34ed68f35e', 'sapphire/general__rusturf_tunnel': 'd3bbc128786e4415876bbe31f20b0ff35f3170d99575b966bf882b34ed68f35e'}}, 'cdb1214ad8f8d3745d794913a2182ab5667534ca3bbe819fc6f019ed9b9f2a27': {'family': 'general__rusturf_tunnel', 'mid': 540, 'source_sha256': {'ruby/general__rusturf_tunnel': 'f5df32e1161649e8569d9175144f644791066d1a65c462a74045313a2af1b98a', 'sapphire/general__rusturf_tunnel': 'f5df32e1161649e8569d9175144f644791066d1a65c462a74045313a2af1b98a'}}, '33f75393711e2cd641dd8b0ecb258b05488e0328c8d4d1c8188680dbb93b80bf': {'family': 'general__rusturf_tunnel', 'mid': 517, 'source_sha256': {'emerald/general__rusturf_tunnel': 'ebe6ecc6775bd2ec7921b6346ff58b95f849d6303c9d0e725760e666d760e21c'}}, '1dadec6cd5ed863ba6bdd04f958fd3820e861c22e24737d48da792320e33fbc2': {'family': 'general__rusturf_tunnel', 'mid': 539, 'source_sha256': {'emerald/general__rusturf_tunnel': '710e8c4252e42b22a0654ead4f67cca0e974d13e0ca2ad5a5aab0c4035eff9b0'}}, 'eb2b14ea8503cbdba7e23da7b333eb22eb07d3c7226ca99abaa70b68dd5f9653': {'family': 'general__rusturf_tunnel', 'mid': 544, 'source_sha256': {'ruby/general__rusturf_tunnel': '12bae53c71fec4418e74f89cb13e67e8ab970355521ce6751fab7fa809848a64', 'sapphire/general__rusturf_tunnel': '12bae53c71fec4418e74f89cb13e67e8ab970355521ce6751fab7fa809848a64'}}, '941b1abc751924be03914c9c225744892b2183031be624a91926698b2e1c33cb': {'family': 'general__rusturf_tunnel', 'mid': 518, 'source_sha256': {'emerald/general__rusturf_tunnel': '4b1d59e156873a88722d53a1268810b64791b2cda0db61d72072461a31aeaa43'}}, '441cb45b48459e43d8e42f12eb07de6510bcd9dc56ecfabb2f03a5a6b3c27a93': {'family': 'general__rusturf_tunnel', 'mid': 538, 'source_sha256': {'emerald/general__rusturf_tunnel': 'b5647105bf255b0d926860b77a1de5b698328194a81d0e8f6ad2fc9d93a427fa'}}, 'a330011cbab882af725a47a70cf451ebd3fec3557dc866b55c551cf4827db345': {'family': 'general__rusturf_tunnel', 'mid': 515, 'source_sha256': {'emerald/general__rusturf_tunnel': 'a47d0c6b2fe5d74bb2f12c2e07c734e360fd3d4625168375ba65d415e61fe818'}}, '6ee87f0ca7bfcc05f1609fc7a6d84eb781f303aef9c6490b0e1c38cc311b356c': {'family': 'general__rusturf_tunnel', 'mid': 516, 'source_sha256': {'ruby/general__rusturf_tunnel': '98ef370f9db8ab0232ffb25cbdfbd858c78b01b86ac8555e8a8d67b83b347559', 'sapphire/general__rusturf_tunnel': '98ef370f9db8ab0232ffb25cbdfbd858c78b01b86ac8555e8a8d67b83b347559'}}, '21a69a1f1eaa001af5c07e4b741ab5225c66126aff56bac7d97782af486ee7c2': {'family': 'general__rusturf_tunnel', 'mid': 520, 'source_sha256': {'ruby/general__rusturf_tunnel': 'bf0bbe768ef49b3fcd6963d0d418e63e7184842abc70d9f5f6e0bb05689d6c40', 'sapphire/general__rusturf_tunnel': 'bf0bbe768ef49b3fcd6963d0d418e63e7184842abc70d9f5f6e0bb05689d6c40'}}, '7e4330eb53ff52a8b7e0e4f0c8cede345a7d03ee182572a3312e8b97c274c1cc': {'family': 'general__rusturf_tunnel', 'mid': 536, 'source_sha256': {'ruby/general__rusturf_tunnel': 'f2d59a0ce585ad806c81bf9396faa51e26898014a5d654ed20eebd5fc9745a54', 'sapphire/general__rusturf_tunnel': 'f2d59a0ce585ad806c81bf9396faa51e26898014a5d654ed20eebd5fc9745a54'}}, '35bfceda6c092af8e2568ee6d4119aaaa51f5ec2dd27ca6a7f76158beba4a645': {'family': 'general__rusturf_tunnel', 'mid': 540, 'source_sha256': {'emerald/general__rusturf_tunnel': 'b37f30367235efa4212366dcb05155e2082819424d7c5e055a629e8cd51e5842'}}, '33ca633c47f1e1683088525aebd518a541c01c2dee163282dbeca1fc363f9dbc': {'family': 'general__rusturf_tunnel', 'mid': 544, 'source_sha256': {'emerald/general__rusturf_tunnel': '34f86377185c7a13c4ce2b0c3846e07bfadd277de2498b1b38db8b38e9b069d3'}}, '32fa8da1ec5123cebce0f94b9a6617f254c867f750b20652c560e2f0ba6f32e1': {'family': 'general__rusturf_tunnel', 'mid': 519, 'source_sha256': {'ruby/general__rusturf_tunnel': '91b6bbd2d1a59eb0516e27f7849b14d1deeab1aa4bc9123c95dc296d770f71a8', 'sapphire/general__rusturf_tunnel': '91b6bbd2d1a59eb0516e27f7849b14d1deeab1aa4bc9123c95dc296d770f71a8'}}, 'a0bec898de0250ab3aaa0108e1574089570da57bdb26ba6dd58c574700ed327b': {'family': 'general__rusturf_tunnel', 'mid': 543, 'source_sha256': {'ruby/general__rusturf_tunnel': 'f097ce9eac650ad087503609d84e8049bdb40051a28ff501c0b7d98547efe6cf', 'sapphire/general__rusturf_tunnel': 'f097ce9eac650ad087503609d84e8049bdb40051a28ff501c0b7d98547efe6cf'}}, 'b55751ba320d882116d4ed9b4e9faf4cb6cbbc3bbf526ea0fd9b5e5e76f42a1d': {'family': 'general__rusturf_tunnel', 'mid': 546, 'source_sha256': {'ruby/general__rusturf_tunnel': 'fbda390dc2941c9342388d0ea5f043f965ea0993bac3d9d1ab785e9d18ae9443', 'sapphire/general__rusturf_tunnel': 'fbda390dc2941c9342388d0ea5f043f965ea0993bac3d9d1ab785e9d18ae9443'}}, '2e0c8ed08cbdacc7842b000fe594fbc27feb5e73a9d3f823740b092a6d08e064': {'family': 'general__rusturf_tunnel', 'mid': 592, 'source_sha256': {'ruby/general__rusturf_tunnel': '9a4a22eeb1ed99235623855bd2258e020d67d4c30c01e822534fa054b9574fa6', 'sapphire/general__rusturf_tunnel': '9a4a22eeb1ed99235623855bd2258e020d67d4c30c01e822534fa054b9574fa6'}}, '7c925e112e063dda3d78fe910515bf28c904ffefec474b8b907dece5521c3a5a': {'family': 'general__rusturf_tunnel', 'mid': 593, 'source_sha256': {'ruby/general__rusturf_tunnel': '8008b78adb17af10b07fd9837e48b26a8e5115a48b26f3881c9013317ec04325', 'sapphire/general__rusturf_tunnel': '8008b78adb17af10b07fd9837e48b26a8e5115a48b26f3881c9013317ec04325'}}, '25fbf2eca59e1f41831df24197caf0df5e3d3f94b2ffa65e8446e3673c2d0052': {'family': 'general__rusturf_tunnel', 'mid': 594, 'source_sha256': {'ruby/general__rusturf_tunnel': 'e3070e4132d95160f06815091188a77e72b74ce5c969b90e38a2f8823ef200d0', 'sapphire/general__rusturf_tunnel': 'e3070e4132d95160f06815091188a77e72b74ce5c969b90e38a2f8823ef200d0'}}, '99cc7efc9b85074af2971fa256741b2d9c538e327e68a0bfe0f0c5decdb07336': {'family': 'general__rusturf_tunnel', 'mid': 516, 'source_sha256': {'emerald/general__rusturf_tunnel': '8452f2da5767269bd88bbecc0e5f3ef4a8e5274d14ef94e9c83cb870596dc334'}}, '8cf776a0351c26ad7c302ac51e6041ba7ef8e91f6bad03846f1ae942c08ff5d1': {'family': 'general__rusturf_tunnel', 'mid': 520, 'source_sha256': {'emerald/general__rusturf_tunnel': 'b78b471844a2140d16e7045cf0e5004c81ac01c65ea48df4e7da522f0c32a01f'}}, '5b24de2df64245e805fa2dcb50435fcc0c5cc65bdfa6fbadd497989c882c761d': {'family': 'general__rusturf_tunnel', 'mid': 536, 'source_sha256': {'emerald/general__rusturf_tunnel': '8e4f29f6ac7a0e44915c41620516043c3ce5c9de91e8376b4d41ebf205facd68'}}, '3b1a206eeeac014a3c3d99e2917e32e3770831cf2ae3dcfdcba06e103f759dbb': {'family': 'general__rusturf_tunnel', 'mid': 519, 'source_sha256': {'emerald/general__rusturf_tunnel': 'd8c2828cbd9e5eb145b6844a7b1b7d7847c6b4c002c581b1132a8286990f485e'}}, '9d78d1ebcd914750604cba9eade2735e9992224cc2a2fcb68ae579827f6d3060': {'family': 'general__rusturf_tunnel', 'mid': 543, 'source_sha256': {'emerald/general__rusturf_tunnel': 'f46ad1823d548edfb2ffd9606b4a86dce4b64c8d25ce34ee23dddff2303f1ac7'}}, 'be390379e1dd46c737de225a4aeb8bc588b112e2c0fcfad64a23db5db6969c99': {'family': 'general__rusturf_tunnel', 'mid': 546, 'source_sha256': {'emerald/general__rusturf_tunnel': 'af592132b7c9e21c7fd0d811baec1e584c788c71c134c9affe909ed4669f1b7e'}}, '3537ce99635d7c43d04a8dd61c609a1de084037e2bc1b70b9423904449a102f2': {'family': 'general__rusturf_tunnel', 'mid': 592, 'source_sha256': {'emerald/general__rusturf_tunnel': '068bdbcdffe3f933b9fe402fc3a5f12e653967a9fa098ee3fc62a199525a3065'}}, '349a54c16542492f3180c20da7a46308c2aea45cc9e453b2d03aa24bc753d6e2': {'family': 'general__rusturf_tunnel', 'mid': 593, 'source_sha256': {'emerald/general__rusturf_tunnel': 'c1e99c1ed7cbce9a4fa802bfd40c31da3e54204f96115b287605862efa47f4ae'}}, 'fad8b2eb465a90cc9f222d44f0266c941ed55ca65c0dcc7283c0aa531d321283': {'family': 'general__rusturf_tunnel', 'mid': 594, 'source_sha256': {'emerald/general__rusturf_tunnel': '14ef5708580e1ec09d5ee10d08dee4cf8bb09e64a06084467b913b7bbc56e28b'}}, '0203434e755afd478090eb3eed13d97edb79dcd8fdd84547e1614094ab2d37d5': {'family': 'general__rusturf_tunnel', 'mid': 522, 'source_sha256': {'ruby/general__rusturf_tunnel': '60f7d2d2a0c6f841ca61861e4893044291c1bd21759f0a40db32e224c5e7fb3d', 'sapphire/general__rusturf_tunnel': '60f7d2d2a0c6f841ca61861e4893044291c1bd21759f0a40db32e224c5e7fb3d'}}, '7665e4fd50f64cab1b67cc30e9c8d61a5f5e3d745b282449552912ea35ef6b01': {'family': 'general__rusturf_tunnel', 'mid': 522, 'source_sha256': {'emerald/general__rusturf_tunnel': '020e74cf5928fbf24f1242851322bcfdcf2e6384fdeed885b7d7c5bfc2fa06a8'}}}

UNDERWATER_SIDE_BINDINGS = {'5a71ab5adedb90bb52255e4996631b531d608c063053d90bebb471795d7b02a0': {'family': 'general__underwater', 'mid': 535, 'source_sha256': {'ruby/general__underwater': 'a43927841d8163ba5561ec5db4143566934df760e3c65332ffbbba46b95c9cb0', 'sapphire/general__underwater': 'a43927841d8163ba5561ec5db4143566934df760e3c65332ffbbba46b95c9cb0', 'emerald/general__underwater': 'a43927841d8163ba5561ec5db4143566934df760e3c65332ffbbba46b95c9cb0'}}, '5676b92a940052acef16c1dcdc312fba455eb6b65c0fe0304a83fdef1a7e3ac6': {'family': 'general__underwater', 'mid': 533, 'source_sha256': {'ruby/general__underwater': '8a98c64322a1397215aed0ed470754c75ec3afb98ca51487f4989bd8c306a3c6', 'sapphire/general__underwater': '8a98c64322a1397215aed0ed470754c75ec3afb98ca51487f4989bd8c306a3c6', 'emerald/general__underwater': '8a98c64322a1397215aed0ed470754c75ec3afb98ca51487f4989bd8c306a3c6'}}, 'dc7d110adc06e060d39e6e4d84fe60cbf99eaa9eb28dcf6162a9d9fcd7fab4b6': {'family': 'general__underwater', 'mid': 542, 'source_sha256': {'ruby/general__underwater': '4340c9f97c6c3dbace91d7f9c380547e5863415147f315ef0398a51b64a98687', 'sapphire/general__underwater': '4340c9f97c6c3dbace91d7f9c380547e5863415147f315ef0398a51b64a98687', 'emerald/general__underwater': '4340c9f97c6c3dbace91d7f9c380547e5863415147f315ef0398a51b64a98687'}}, '5b736071503ef61e8e349cbfd97723b84592493561716da3080a9e56859458fb': {'family': 'general__underwater', 'mid': 681, 'source_sha256': {'ruby/general__underwater': 'c25dc1dff00b7a9ae8994e42b0ed02f93f7cd52c57565cc2a19647125d311ac5', 'sapphire/general__underwater': 'c25dc1dff00b7a9ae8994e42b0ed02f93f7cd52c57565cc2a19647125d311ac5', 'emerald/general__underwater': 'c25dc1dff00b7a9ae8994e42b0ed02f93f7cd52c57565cc2a19647125d311ac5'}}, '6c74935eb706ca7e1265b930c663b33bde1fad9da5ecc8cb2f680dc6cf97c8d7': {'family': 'general__underwater', 'mid': 644, 'source_sha256': {'ruby/general__underwater': '69ef667bb020c92ba9fe01e45a979a219c096af100ae0aaa104bc13d71ae2377', 'sapphire/general__underwater': '69ef667bb020c92ba9fe01e45a979a219c096af100ae0aaa104bc13d71ae2377', 'emerald/general__underwater': '69ef667bb020c92ba9fe01e45a979a219c096af100ae0aaa104bc13d71ae2377'}}, 'e967c440293567e5272c9ce0ad8e3e4b13df535362adf11e27782e70c3da06b9': {'family': 'general__underwater', 'mid': 654, 'source_sha256': {'ruby/general__underwater': '1c714e13c2778ab500beb939c2a32cd6d2eeeec67385dc9569bc2a3d2f383762', 'sapphire/general__underwater': '1c714e13c2778ab500beb939c2a32cd6d2eeeec67385dc9569bc2a3d2f383762', 'emerald/general__underwater': '1c714e13c2778ab500beb939c2a32cd6d2eeeec67385dc9569bc2a3d2f383762'}}, '636c372cd1fa75bbc0301643cc9306e4e2014d93b54ef5e10cc0a1f984e86dec': {'family': 'general__underwater', 'mid': 653, 'source_sha256': {'ruby/general__underwater': 'e3cd6b53cea827ddaeec97865fd19d03260ef38fe14eed77469faf0c86ff6546', 'sapphire/general__underwater': 'e3cd6b53cea827ddaeec97865fd19d03260ef38fe14eed77469faf0c86ff6546', 'emerald/general__underwater': 'e3cd6b53cea827ddaeec97865fd19d03260ef38fe14eed77469faf0c86ff6546'}}}

LIMESTONE_WALL_BINDINGS = {'c7d12af0ee36ba9c914b99580f0b39b591907eedd414a53c6b4e5525f90176cb': {'family': 'general__sootopolis', 'mid': 737, 'source_sha256': {'ruby/general__sootopolis': 'c17d74bee3840800f644a1643bbcb57a3b3ca50e356c5a4a5ce8c1b8cb464353', 'sapphire/general__sootopolis': 'c17d74bee3840800f644a1643bbcb57a3b3ca50e356c5a4a5ce8c1b8cb464353'}}, 'e333ddc38a2111910600f2038f302b2ff9b1bb83e52a998b960f2c83ff5ac14c': {'family': 'general__sootopolis', 'mid': 730, 'source_sha256': {'ruby/general__sootopolis': '77719170cfc144ebe892859bbc8a79770924252f0677ec32ff4de5f32b2230bd', 'sapphire/general__sootopolis': '77719170cfc144ebe892859bbc8a79770924252f0677ec32ff4de5f32b2230bd', 'emerald/general__sootopolis': '77719170cfc144ebe892859bbc8a79770924252f0677ec32ff4de5f32b2230bd'}}, '0802f29bdacb28212f7ee29d3fc10f72908801d7dfeb4115d733d012bba30295': {'family': 'general__sootopolis', 'mid': 728, 'source_sha256': {'ruby/general__sootopolis': 'b4ed8715182514c8535820397b27fc40ef76b1dd5ea9f6885fcecdf69a58dd25', 'sapphire/general__sootopolis': 'b4ed8715182514c8535820397b27fc40ef76b1dd5ea9f6885fcecdf69a58dd25', 'emerald/general__sootopolis': 'b4ed8715182514c8535820397b27fc40ef76b1dd5ea9f6885fcecdf69a58dd25'}}, '63a1fee70beb5187e3e31bc4dbbaeb81637671be8a52c0733271aa4d14d324c0': {'family': 'general__sootopolis', 'mid': 737, 'source_sha256': {'emerald/general__sootopolis': 'cc1d047e191ec94cba5a31de209b36c0223d535f0f611f4d293354efb054b423'}}, '21e594088c93662fc09287f522bf3ae15b1c5aef318a3ef5c0a6209ad59b7f6c': {'family': 'general__sootopolis', 'mid': 723, 'source_sha256': {'ruby/general__sootopolis': '99d5daccc78c0f56178671e53e9bf19ea2b6c40b6b46680756dc2a58ec325386', 'sapphire/general__sootopolis': '99d5daccc78c0f56178671e53e9bf19ea2b6c40b6b46680756dc2a58ec325386', 'emerald/general__sootopolis': '99d5daccc78c0f56178671e53e9bf19ea2b6c40b6b46680756dc2a58ec325386'}}, '74ded15bb94303a995bb3b3f366a7a38ae6a6c147b2ba3f88dae840813ba702e': {'family': 'general__sootopolis', 'mid': 724, 'source_sha256': {'ruby/general__sootopolis': 'd6b011187ddbbd7ede3b6e61e8882286149e6798ce36e7601a6e170452882bc0', 'sapphire/general__sootopolis': 'd6b011187ddbbd7ede3b6e61e8882286149e6798ce36e7601a6e170452882bc0', 'emerald/general__sootopolis': 'd6b011187ddbbd7ede3b6e61e8882286149e6798ce36e7601a6e170452882bc0'}}, 'ff3e736aa06a388bfe826d069454d4e5d97b34993ba0fc4d1175c694ae38f5d6': {'family': 'general__sootopolis', 'mid': 738, 'source_sha256': {'ruby/general__sootopolis': 'a810e0324f74aec3c432113b7d7110a6115ddcfc5c7991f488abbbf4e8888162', 'sapphire/general__sootopolis': 'a810e0324f74aec3c432113b7d7110a6115ddcfc5c7991f488abbbf4e8888162', 'emerald/general__sootopolis': 'a810e0324f74aec3c432113b7d7110a6115ddcfc5c7991f488abbbf4e8888162'}}, '770e22bcd8f755f0223e2de635e4f2aaa4449d29a426526a96000d420eaed817': {'family': 'general__sootopolis', 'mid': 736, 'source_sha256': {'ruby/general__sootopolis': '8d3e4f3ffc997fba3c74b1f2aae212c59eb8eb123ac99f3ede8cc98560559a71', 'sapphire/general__sootopolis': '8d3e4f3ffc997fba3c74b1f2aae212c59eb8eb123ac99f3ede8cc98560559a71', 'emerald/general__sootopolis': '8d3e4f3ffc997fba3c74b1f2aae212c59eb8eb123ac99f3ede8cc98560559a71'}}}

VOLCANIC_CORE_BINDINGS = {'1e967f1ca4aea1b5a6fa7f3da5dd29a762624ca2d69d0645102ef04b06e61422': {'family': 'general__lavaridge', 'mid': 626, 'source_sha256': {'ruby/general__lavaridge': 'b99aecc65d5a105e1acb0b82c9b0ee97b9b377d07ff0842b628f273ac656b8cf', 'sapphire/general__lavaridge': 'b99aecc65d5a105e1acb0b82c9b0ee97b9b377d07ff0842b628f273ac656b8cf', 'emerald/general__lavaridge': 'b99aecc65d5a105e1acb0b82c9b0ee97b9b377d07ff0842b628f273ac656b8cf'}}, 'ac5bf072d067dccb1a6b2f39ec3cbaac7e15d35baec660db11d822bcd345c00d': {'family': 'general__lavaridge', 'mid': 628, 'source_sha256': {'ruby/general__lavaridge': '259b97873c8453f137f9d6aed1702063eef0f71a26a84037b3c0df90cfab042a', 'sapphire/general__lavaridge': '259b97873c8453f137f9d6aed1702063eef0f71a26a84037b3c0df90cfab042a', 'emerald/general__lavaridge': '259b97873c8453f137f9d6aed1702063eef0f71a26a84037b3c0df90cfab042a'}}, '7470237fae23752d8e0734b21e53f08f03574182144cfa1bb63a0086a315677d': {'family': 'general__lavaridge', 'mid': 776, 'source_sha256': {'ruby/general__lavaridge': '8302b158ae7b9066752b256e3e835a15206ed73eb8ec7e0f9964017a22f2f203', 'sapphire/general__lavaridge': '8302b158ae7b9066752b256e3e835a15206ed73eb8ec7e0f9964017a22f2f203', 'emerald/general__lavaridge': '8302b158ae7b9066752b256e3e835a15206ed73eb8ec7e0f9964017a22f2f203'}}, '44212edbce9a41d663d732d779d59a8123a7dcb4c82a2e0593e31fb739967f8f': {'family': 'general__lavaridge', 'mid': 624, 'source_sha256': {'ruby/general__lavaridge': '6612ee62fa31fe1f38fb11799355b4ea2843923c1ab1c58917877da4a3c1b1c7', 'sapphire/general__lavaridge': '6612ee62fa31fe1f38fb11799355b4ea2843923c1ab1c58917877da4a3c1b1c7', 'emerald/general__lavaridge': '6612ee62fa31fe1f38fb11799355b4ea2843923c1ab1c58917877da4a3c1b1c7'}}, '6fbabbc8193df91f35c6a7c8e7f79ee9f0512e0bb447d22de5c66f03ba6ce669': {'family': 'general__lavaridge', 'mid': 774, 'source_sha256': {'ruby/general__lavaridge': '6612ee62fa31fe1f38fb11799355b4ea2843923c1ab1c58917877da4a3c1b1c7', 'sapphire/general__lavaridge': '6612ee62fa31fe1f38fb11799355b4ea2843923c1ab1c58917877da4a3c1b1c7', 'emerald/general__lavaridge': '6612ee62fa31fe1f38fb11799355b4ea2843923c1ab1c58917877da4a3c1b1c7'}}, 'a41a63ef735bfaadede81ab5859db863144e603ce2f3cf24933912149d8bee20': {'family': 'general__lavaridge', 'mid': 634, 'source_sha256': {'ruby/general__lavaridge': 'a5d871c378b180dec8434c25576436781d5d9bfe2e91fe3c3b348ad36c9569ad', 'sapphire/general__lavaridge': 'a5d871c378b180dec8434c25576436781d5d9bfe2e91fe3c3b348ad36c9569ad', 'emerald/general__lavaridge': 'a5d871c378b180dec8434c25576436781d5d9bfe2e91fe3c3b348ad36c9569ad'}}, 'f3a5054d3daae25c715f3a650fa95a517a7716976b38ec828fd030a366b44ed9': {'family': 'general__lavaridge', 'mid': 930, 'source_sha256': {'emerald/general__lavaridge': 'c29ba3b98f3de3201441095fdccd7caa066c4ac3dcaffa4f13de645d9bdda4d3'}}, '3d5e9c4212e3acd10d35938432e897c0a766e398d2b9c886646d4b4245b2e7b6': {'family': 'general__lavaridge', 'mid': 632, 'source_sha256': {'ruby/general__lavaridge': '292a8176d32f7842b1bac60b0d93559d6746b82cad67577eef0d29873f07c8ca', 'sapphire/general__lavaridge': '292a8176d32f7842b1bac60b0d93559d6746b82cad67577eef0d29873f07c8ca', 'emerald/general__lavaridge': '292a8176d32f7842b1bac60b0d93559d6746b82cad67577eef0d29873f07c8ca'}}, '65a78d062feca66d9d252e92b453fc0aa77c46edbfada72eae4a3534d8dd7c53': {'family': 'general__lavaridge', 'mid': 639, 'source_sha256': {'ruby/general__lavaridge': '3ef0abfb99c25fa4f32e583421c7e87e483d6b759c17fb4dbbf4e601bbe3d6db', 'sapphire/general__lavaridge': '3ef0abfb99c25fa4f32e583421c7e87e483d6b759c17fb4dbbf4e601bbe3d6db', 'emerald/general__lavaridge': '3ef0abfb99c25fa4f32e583421c7e87e483d6b759c17fb4dbbf4e601bbe3d6db'}}, 'ae1f82395d703cd802da05d1378494f6938f394cd5140695d5ee7d1e6afeb211': {'family': 'general__lavaridge', 'mid': 638, 'source_sha256': {'ruby/general__lavaridge': '8341d6810f8b30be567e59351ad01d1cea670c23ac24658598856ec80f485fc8', 'sapphire/general__lavaridge': '8341d6810f8b30be567e59351ad01d1cea670c23ac24658598856ec80f485fc8', 'emerald/general__lavaridge': '8341d6810f8b30be567e59351ad01d1cea670c23ac24658598856ec80f485fc8'}}}

COAST_ROCK_BINDINGS = {'e032a9d15a30b2909b6a1010cef55e5a36ddd416943a74bc63a3ebd461e72276': {'family': 'primary', 'mid': 380, 'source_sha256': {'ruby/general__cave': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'ruby/general__dewford': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'ruby/general__ever_grande': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'ruby/general__fortree': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'ruby/general__lilycove': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'ruby/general__mossdeep': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'ruby/general__pacifidlog': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'ruby/general__rustboro': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'ruby/general__slateport': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__cave': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__dewford': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__ever_grande': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__fortree': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__lilycove': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__mossdeep': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__pacifidlog': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__rustboro': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'sapphire/general__slateport': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__cave': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__dewford': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__ever_grande': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__fortree': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__lilycove': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__mossdeep': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__pacifidlog': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__rustboro': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5', 'emerald/general__slateport': '4e8353beb3ef8295168bd4a82dcebca3330c39c29b19f83a8390a56eabed44e5'}}, 'b199355cb06a52d3c2c9b8eebd9814d649de06ff3438631ea2a4124f8c1fb264': {'family': 'primary', 'mid': 373, 'source_sha256': {'ruby/general__cave': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__dewford': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__ever_grande': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__fallarbor': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__lilycove': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__pacifidlog': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__petalburg': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__rustboro': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__slateport': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__cave': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__dewford': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__ever_grande': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__fallarbor': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__lilycove': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__pacifidlog': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__petalburg': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__rustboro': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__slateport': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__cave': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__dewford': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__ever_grande': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__fallarbor': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__lilycove': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__pacifidlog': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__petalburg': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__rustboro': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__slateport': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41'}}, '58276e6ab4985f0e756b4f40c4ec2acc5e0d43e65800e9790dc1f0a453c7f2e9': {'family': 'primary', 'mid': 374, 'source_sha256': {'ruby/general__cave': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__dewford': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__ever_grande': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__fallarbor': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__lilycove': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__mossdeep': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__pacifidlog': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__petalburg': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__rustboro': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'ruby/general__slateport': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__cave': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__dewford': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__ever_grande': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__fallarbor': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__lilycove': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__mossdeep': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__pacifidlog': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__petalburg': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__rustboro': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__slateport': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__cave': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__dewford': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__ever_grande': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__fallarbor': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__lilycove': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__mossdeep': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__pacifidlog': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__petalburg': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__rustboro': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__slateport': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a'}}, '3b6537866cfe63fa818aac2173f22ae48588d6c0b194a5ade0ea1d3e96a8fac9': {'family': 'general__mossdeep', 'mid': 829, 'source_sha256': {'ruby/general__mossdeep': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'sapphire/general__mossdeep': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a', 'emerald/general__mossdeep': '9defa9840802b375dc64fc635c5494c9ada94dd58503bce689efdf0ba87ed17a'}}, '6c4f494b8e73fee0b604cf641fd8c88f9eef87c5a59179b4d915f9f1976a17ac': {'family': 'general__mossdeep', 'mid': 827, 'source_sha256': {'ruby/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41'}}, 'eb4a03fa278d2661c59ffed26f6ecc701c54c6bc2b7203400dd42c928c83c45c': {'family': 'general__mossdeep', 'mid': 828, 'source_sha256': {'ruby/general__mossdeep': '7c47e4fa5121c54cfa2d85a25359dc079d997c82555cd4881a95f4423472e7f9', 'sapphire/general__mossdeep': '7c47e4fa5121c54cfa2d85a25359dc079d997c82555cd4881a95f4423472e7f9', 'emerald/general__mossdeep': '7c47e4fa5121c54cfa2d85a25359dc079d997c82555cd4881a95f4423472e7f9'}}, '2ee84ee68b3e464b92c465eae91eccd1b93b02ce6b87f73f0b5fcc609470d685': {'family': 'primary', 'mid': 370, 'source_sha256': {'ruby/general__cave': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__dewford': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__ever_grande': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__facility': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__fallarbor': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__lilycove': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__pacifidlog': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__rustboro': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'ruby/general__slateport': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__cave': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__dewford': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__ever_grande': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__facility': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__fallarbor': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__lilycove': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__pacifidlog': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__rustboro': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'sapphire/general__slateport': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__battle_frontier_outside_east': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__battle_frontier_outside_west': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__cave': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__dewford': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__ever_grande': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__facility': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__fallarbor': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__lilycove': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__mossdeep': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__pacifidlog': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__rustboro': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41', 'emerald/general__slateport': '48254ceebee758b07ff27953b0a191f11a0df2cfe556e5649167473f8e014e41'}}, 'a57c9db508f16c82c6215bb5df28d365154aace9c3404ca72846af962b09c6ec': {'family': 'general__mossdeep', 'mid': 837, 'source_sha256': {'ruby/general__mossdeep': 'abaf85f44e87f11ac8755d14d91aec591d2a4261af22dee17a0b0c883d4bb7d7', 'sapphire/general__mossdeep': 'abaf85f44e87f11ac8755d14d91aec591d2a4261af22dee17a0b0c883d4bb7d7', 'emerald/general__mossdeep': 'abaf85f44e87f11ac8755d14d91aec591d2a4261af22dee17a0b0c883d4bb7d7'}}}

COAST_SE_FIX_BINDINGS = {'ruby/general__cave/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'b5b744708486286bf56e3bcc3ed2e84e17a885b2b92ebe687bf5a0f8c3919fbc', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__dewford/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '65c84de9df977bbacfb5b34b92de27b884c4d9ca1ab35b44e63cd8a4475c0cea', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__ever_grande/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '41699e2420e128ccd224976c619597e59852a59f4f82d92642e5cbbb4d1a95de', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__fallarbor/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '92e400fd0d15cb3de0d2be29e447c407d67b1c6d04d21ff8466d7626b0fbfbd1', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__lilycove/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '86b1af5abaec87db1b621769a83553f750ece7dadcbae6021e268cda482bb2fc', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__mossdeep/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'efd505bfa8a5e0e71f6449139b4725fa8ab24e6bd9e5add4285a100848c8537c', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__pacifidlog/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '45925307572f0eb9a75ccc6f104fcc9e8f53bf28e8aca98c72676f6a571d8b13', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__petalburg/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '9e444d837bfb5cfafc94c2c19c5cee7cdd625c427fb2ae76475ab2082e525778', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__rustboro/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'a5d7d699ebd7981221c727f2d4d7b1d49dad91f5a94dd91227f49dc12992af4d', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__slateport/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '44c8c6eda14382ab594e15723a2bfd45bc08597ca1f929557f19bf5a9b3b8366', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__cave/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '302a1e2a84e9ce2fd38bea68562fecb09d79b9a7164700b876d04624d11de2f9', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__dewford/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'bde95d13e2bd629860bfc6d01088a5e4d11a40425550919a4053b5441357a62b', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__ever_grande/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'dc016f3fd5cf56f54eb20b9152b2a506f5d294ba1a647ae59a74b97f380b1822', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__fallarbor/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'be8a9949e985370cd79b0eca41e870d9d620b2a9e4e4bd80f277d9dcf285f6f9', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__lilycove/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '3bf65de0ca3666de0833ab378a4930306a48cbee725d46d723bfdec0f85bba4f', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__mossdeep/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '56694865ec5a0499e8bdb51d223e9137c7e13343a559470f6e349c6d9e631734', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__pacifidlog/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '033c0b45f98c5e086f141ca406faa2a24f2794c8d379cbadf6bb6c1363882df9', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__petalburg/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'dae1fe4dd257c1816ebcb6b4bfd0928b34fd33d82501c4dc8f4c09a59477e05a', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__rustboro/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'b2337890ab24f345261b4e779caacc0fec15e64e5f07719e8f354187c29f6f3b', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__slateport/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '80b973e6453d94c2533370b6e4c9e525209880730c10a4ad9a9b941506a62581', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__cave/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '97fc433bf6be6ee35f268fb61b0d3fca13b579aa2e667942193ce6d0ceffbf79', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__dewford/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'f68d50f820e0562a31eceb4c1424dcd7a680c47052602b58a67778b2eb3c3e00', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__ever_grande/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '45c30bfaf795c557d5682122701cae5826b7ff8270bdde9f6f2131691a95bd6e', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__fallarbor/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'c84491c7d6a3b527918358cb9f94a13f5a5e0837366ed8baf3599cad159f9781', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__lilycove/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'd60b6a99616cf42b3804fb4eed0ab4c4bdd8d36e638f432d9daa4803c5ab0efc', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__mossdeep/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '1f0b48aab2e2f1a073dbbc46f8045f56e478a19803f8b0a13f90ee6105de0364', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__pacifidlog/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '40fde8b823887a25c9bfcda3d609a103e48740705158a8c32a10e72fb7823c2d', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__petalburg/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '65e10ab05531c32e7439c6f50b4396983c5c77a1cbbe3204b08db5db1369c50c', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__rustboro/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'f7894085cdedddc3fa9c3bf8ecbcd2472b9a78cba1744bbca92b7bf4adeec35b', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__slateport/382': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'f2a83ec286c59b4715d70d5f4395cb68dec56571ec77ad4f2383a3f5bc9976e1', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__cave/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '754cc29f5f289d50996886b934c072ca3a3a7c4dd33c90e8749f2db37a62d33d', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__dewford/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '48caaae5a6a3f9c982198e437dc3e12c55419bccfda4e104902ace7ff07a1a59', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__ever_grande/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'cfa782ccba17251117d2408b363d9c5386fe57998c2563ed4f292f8ad74e5687', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__fortree/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'efe55ed0e5454ab7a543cf60a1312caaa84d303c6c7aed77cbdd89c81dc22ae4', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__lilycove/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'e4757cd1885718d4116fed65b10b010d7eab7697d2f058dd916295d3fa0b4fcf', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__mossdeep/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '3b9e0ba00aa985f3d53ca0a4a070a33f5e43f635903f9f70058f20942b032fd3', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__pacifidlog/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'f61c17c2556b3bee773834b9cceff2bdb8ba5612bee0e27acb2947fd9919c963', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__rustboro/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '691839235cdfe5c93fd481a7a0161a8aeaff058cb06fd6fa2dbdb963b472d256', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'ruby/general__slateport/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '026855484949d0a479749fe47971c9b5dec3decf3da2cdbb5cbf2ddf31f939d2', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__cave/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '4206d838096e338238da13c13231a04b16dfdfabfe637d4c9ac0f67b8c1b2917', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__dewford/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '1108b4140946411af70ed3840419923d83f3acff63c9d7260e46d3bda1cc2b1c', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__ever_grande/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'b49ccb3190e5c76fd4fdcd67b2b59a26576eb1752114755d6336645930fb33ba', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__fortree/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '7907913bafa733c8e769ac3543b69d571db0d46aa2c61cb3825c43fceafca7d4', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__lilycove/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '5519485546ede15625df28d92aedbcbec23e378baefafda2ddce0d94b7566594', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__mossdeep/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '38b5922d9b778ce381e37f832ee7123a4634223d16bd5df0e864cc4f9e5c5e12', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__pacifidlog/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'f967647890506bdcb991f318a992df7175372d24dd45caf51b66edb469e9db34', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__rustboro/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '9da2df5989d4f8a8f0500b3706c8183ab26f9abef528fb8495b848217a9d7a88', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'sapphire/general__slateport/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'aa69ef1552edf1a2b46ec569ade9492b12da0cce9bed024f503ed672e136fcbe', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__cave/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'b0f266f68e338fc60b516be0194009dc523f07a7c83049bc6a6541ff5bcfa53d', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__dewford/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '15a859bb711b8ff280de06a147a0fbe4f836b8ac19a5d3b1b57d87e422d83191', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__ever_grande/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'f9206c7eb834383123b064a506993b27300f47814a6c1ba486642e429d4a770f', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__fortree/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'f993ae9dbfec404872803609defed0164055f3aad69f2c3a2cf63386c1850c92', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__lilycove/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '6c2614a98f094d229591e64ec243d055be8c826af3aed9ecd43d23db2d14dde2', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__mossdeep/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'cf62d17179142869004a950d562c0a31dbbe89a01b67b7294a057588532bb4d4', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__pacifidlog/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'e65143e91d2eb07ab9ffb4b6b1e62799a43591c0be00cd33fb30cb7713b3f5bb', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__rustboro/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': '2805c5355fb492ff21a80cbca8c74b5d9bda1cccc4fea33e01f93ee14041ab82', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}, 'emerald/general__slateport/388': {'module': 'mappings/reverse_gen2_hoenn_outdoor_finish.lua', 'full_old_row_sha256': 'bbd04cf3522bffba9f677cc5c9a0acb93d5321e536ae3e624a52b1ef74681550', 'source_hash': '8f09e61fb6db7cf91cd365f007d678b056f0c9666c4596470bacc18e6958e098'}}


class Review(PreviousReview):
    def __init__(self):
        ReverseReview.__init__(self, 'gen2-hoenn-outdoor-complete', GAMES)
        self.target_module = TARGET
        self.prior = []
        self.locations = {}
        for name in dict.fromkeys(re.findall(r"['\"](mappings/[^'\"]+\.lua)['\"]", (ROOT / 'main.lua').read_text())):
            if ROOT / name == TARGET:
                continue
            for number, row in enumerate(preview.read_reviewed(ROOT / name)):
                self.prior.append(row)
                self.locations[identity(row)] = (name, number, row)
        self.occupied = {identity(row) for row in self.prior}
        self.templates = preview.read_reviewed(TARGET) if TARGET.exists() else []
        self.groups = {}
        self.group_list = []
        self.counts = Counter()
        self.collision_profiles = defaultdict(Counter)
        self.usage = defaultdict(list)
        self.proofs = {}
        self.recipes = {}
        self.supersessions = {}
        self.uncertain = []
        self.layouts = {}
        self.layout_hashes = {}
        self._source_maps = {}
        self._rendered_rows = {}

    def native_layout(self, game, name):
        key = game, name
        if key in self.layouts:
            return self.layouts[key]
        spec = self.imp.table(game, 'gba/native/manifest')['layouts'][name]
        path = self.cache / game / 'data/generated/gba/native' / spec['file']
        raw = path.read_bytes()
        self.layout_hashes[path.relative_to(self.cache).as_posix()] = hashlib.sha256(raw).hexdigest()
        blob = raw if raw[:4] == b'SVML' else zlib.decompress(raw)
        assert blob[:4] == b'SVML'
        width, height, logical_width, logical_height = struct.unpack_from('<HHHH', blob, 6)
        columns, lines = logical_width or width, logical_height or height
        offset = 16 + blob[14] * blob[15] * 2
        cells = [struct.unpack_from('<HBB', blob, offset + (y * width + x) * 4)
                 for y in range(lines) for x in range(columns)]
        result = dict(pair=spec['pair'], width=columns, height=lines, storage_width=width,
                      storage_height=height, cells=cells, mids=[c[0] for c in cells])
        self.layouts[key] = result
        return result

    def inventory(self, contacts=True):
        for game in GAMES:
            index = self.imp.cell_index(game)
            for name, spec in self.imp.table(game, 'gba/native/manifest')['layouts'].items():
                if not spec['pair'].startswith('general__'):
                    continue
                layout = self.native_layout(game, name)
                positions = defaultdict(list)
                for number, (mid, coll, elev) in enumerate(layout['cells']):
                    if scope(layout['pair'], mid):
                        positions[mid].append([number % layout['width'], number // layout['width'], coll, elev])
                        self.collision_profiles[game, layout['pair'], mid][coll, elev] += 1
                for mid, coordinates in positions.items():
                    key = game, layout['pair'], mid
                    self.counts[key] += len(coordinates)
                    self.usage[key].append(dict(map=name, count=len(coordinates), coordinates=coordinates[:12]))
            for (pair, mid), cell in index.items():
                if not scope(pair, mid) or not self.counts[game, pair, mid]:
                    continue
                geometry = [catalog.sha(part) for part in native_geometry(self, game, pair, mid)]
                family = 'primary' if mid < 512 else pair
                sig = digest([family, mid, cell['behavior'], geometry])
                group = self.groups.setdefault(sig, dict(family=family, mid=mid, source_identity=sig,
                                                         geometry=geometry, source=[], existing=[], missing=[]))
                item = dict(game=game, pair=pair, mid=mid, hash=cell['pixel_sha256'], behavior=cell['behavior'],
                            behavior_hint=cell.get('behavior_hint'), category=cell.get('native_category'),
                            occurrences=self.counts[game, pair, mid], contexts=self.usage[game, pair, mid],
                            collision_elevation_modes=[list(value) for value in sorted(self.collision_profiles[game, pair, mid])])
                group['source'].append(item)
                group['existing' if (game, 'gen2', pair, mid, None) in self.occupied else 'missing'].append(item)
        self.group_list = sorted((g for g in self.groups.values() if g['missing']),
                                 key=lambda g: (-sum(s['occurrences'] for s in g['missing']), g['family'], g['mid'], g['source_identity']))
        for number, group in enumerate(self.group_list):
            group['review_index'] = number
        (self.out / 'inventory.json').write_text(json.dumps(self.group_list, indent=2) + '\n')
        (self.out / 'source-layout-hashes.json').write_text(json.dumps(self.layout_hashes, indent=2) + '\n')
        if contacts:
            self.contacts(self.group_list, 'missing-contact')
        summary = dict(missing_groups=len(self.group_list), missing_source_keys=sum(len(g['missing']) for g in self.group_list),
                       missing_logical_cells=sum(s['occurrences'] for g in self.group_list for s in g['missing']),
                       logical_layouts=len(self.layouts), preserved_active_keys=len(self.occupied))
        (self.out / 'inventory-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        return summary

    def contacts(self, groups, stem):
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 11)
        for start in range(0, len(groups), 64):
            panel = Image.new('RGB', (8 * 156, 8 * 124 + 36), '#18212b')
            draw = ImageDraw.Draw(panel)
            draw.text((8, 8), 'Actual-used missing native cells; contact order is not an equivalence binding', fill='white', font=font)
            for number, group in enumerate(groups[start:start + 64]):
                source = next((s for s in group['missing'] if s['game'] == 'emerald'), group['missing'][0])
                image = preview.native_donor(self.cache, dict(game=source['game'], tileset=source['pair'], id=source['mid'], hash=source['hash']), self.packed)
                x, y = number % 8 * 156, number // 8 * 124 + 36
                panel.paste(image.resize((64, 64), Image.Resampling.NEAREST), (x + 4, y + 20))
                draw.text((x + 4, y + 2), f"{group['review_index']}: MID {group['mid']}", fill='white', font=font)
                draw.text((x + 72, y + 20), source['pair'].replace('general__', '')[:13] + '\n' + str(source['behavior_hint'])[:13] + '\n' + str(sum(s['occurrences'] for s in group['missing'])), fill='#cbd6e3', font=font)
                draw.text((x + 4, y + 89), source['contexts'][0]['map'][3:25], fill='#a9c6d5', font=font)
            panel.save(self.out / f'{stem}-{start // 64 + 1:02}.png')

    def emit_checked(self, group, art, reason, proof):
        assert group['source_identity'] not in self.recipes
        contract = dict(source_family=group['family'], source_mid=group['mid'],
                        source_geometry_behavior_identity=group['source_identity'],
                        source_geometry_sha256=group['geometry'], proof=copy.deepcopy(proof), pixel_scale=1)
        self.recipes[group['source_identity']] = dict(art=copy.deepcopy(art), reason=reason, contract=contract)
        for source in group['missing']:
            row = self.row(source['game'], source['pair'], source['mid'], 'gen2', art,
                           reason + ' Actual logical native-layout contexts and per-cartridge indexed geometry, all source RGBA planes and behavior are checked. Complete native GB features retain original pixel size. Source collision, elevations, events, warps, scripts, actors and positions remain unchanged.')
            row['reverseGen2HoennOutdoorComplete'] = copy.deepcopy(contract)

    @staticmethod
    def clipped_parts(art, mask):
        parts = art.get('parts') or [dict(donor=art['donor'], w=16, h=16)]
        out = []
        for part in parts:
            covered = [mask[i] and part.get('x', 0) <= i % 16 < part.get('x', 0) + part['w']
                       and part.get('y', 0) <= i // 16 < part.get('y', 0) + part['h'] for i in range(256)]
            for span in runs(covered):
                piece = copy.deepcopy(part)
                piece.update(srcX=part.get('srcX', 0) + span['x'] - part.get('x', 0),
                             srcY=part.get('srcY', 0) + span['y'] - part.get('y', 0), **span)
                out.append(piece)
        return out

    def active_art(self, game, pair, mid):
        row = self.locations[game, 'gen2', pair, mid, None][2]
        art = artwork(row)
        for field in ('role', 'overMask', 'animationCategory'):
            if field in row:
                art[field] = copy.deepcopy(row[field])
        return art

    def limestone_floor(self):
        # Actual Sootopolis729 occurs on both walkable terraces and blocked
        # backfill; its picture is flat limestone, not a vertical cliff face.
        # Keep the original Crystal rough-stone floor geometry and its actual
        # native gray-stone palette, rather than using a grass corner base.
        definition = self.imp.table('crystal', 'maps')['SAFFRON_CITY']
        palette = preview.palette_set(self.imp.table('crystal', 'palettes'), definition, 'DAY')[0]
        assert palette == [[222, 255, 222], [173, 173, 173], [107, 107, 107], [58, 58, 58]]
        ref = self.gb_ref('crystal', 'UNION_CAVE_1F', 2, 0)
        ref['palettes'] = [copy.deepcopy(palette) for _ in range(8)]
        art = self.native(ref, 'reverse_gen2_hoenn_sootopolis_flat_limestone_surface')
        art['overMask'] = '0' * 256
        proof = dict(native_ref=ref, native_geometry=['crystal', 'UNION_CAVE_1F', 2, 0],
                     native_palette_source=['crystal', 'SAFFRON_CITY', 'DAY', 0],
                     native_dimensions=[16, 16], pixel_scale=1,
                     source_feature='Sootopolis729 flat walkable limestone / matching blocked backfill;737 cliff face remains separate',
                     source_context='sootopolis-contexts.json')
        (self.out / 'native-limestone-floor-contract.json').write_text(json.dumps(dict(art=art, proof=proof), indent=2) + '\n')
        self.render(art).save(self.out / 'native-limestone-floor16.png')
        return art, proof

    def rusturf_core(self):
        # Reviewed joined Rusturf grid:513/514 are the actual traversable
        # cave floor,529 is raised backing, and572 is a SOUTH LEDGE rather
        # than a cave portal. The ledge's complete cap family stays separate.
        refs = {513:(2,0), 514:(2,0), 515:(24,0), 516:(24,0), 517:(14,2), 518:(14,3),
                519:(36,3), 520:(4,0), 521:(4,1), 522:(6,1), 528:(4,2), 529:(4,3), 530:(6,3),
                536:(12,2), 537:(12,3), 538:(14,3), 539:(16,3), 540:(17,2), 543:(18,3),
                544:(4,0), 546:(6,1), 592:(35,0), 593:(35,1), 594:(35,0)}
        for group in self.group_list:
            binding = CORE_CAVE_BINDINGS.get(group['source_identity'])
            if binding is None:
                continue
            assert (group['family'], group['mid']) == (binding['family'], binding['mid'])
            assert {s['game'] + '/' + s['pair']: s['hash'] for s in group['source']} == binding['source_sha256'], 'Reviewed natural source RGBA changed'
            if group['family'] == 'general__sootopolis':
                art, proof = self.limestone_floor()
                reason = 'The actual native Sootopolis729 picture is the same flat limestone on walking terraces and blocked backfill. It uses the complete original Crystal rough-stone floor in the actual original gray-stone DAY palette. Vertical limestone faces/corners remain distinct cells; neither a grassy exterior base nor a filled cliff face is substituted for this floor.'
            else:
                mid = group['mid']
                bid, q = refs[mid]
                ref = self.gb_ref('crystal', 'UNION_CAVE_1F', bid, q)
                art = self.native(ref, 'reverse_gen2_hoenn_rusturf_native_' + str(mid))
                art['overMask'] = '0' * 256
                proof = dict(native_ref=ref, source_context='rusturf-contexts.json',
                             native_dimensions=[16,16], source_family='ordinary cave, not encounter grass',
                             raised_source_fill=529, actual_source_walk_floor=[513,514],
                             source_south_exits=[['EM_ROUTE116',4,10],['EM_VERDANTURF_TOWN',29,16],['EM_ROUTE116',18,20]])
                reason = 'The complete original Rusturf joined map distinguishes the actual traversable cave floor513/514 from raised backing529 and all handed wall joins. The exact corresponding complete original Crystal cave floor, raised stone, boulder, directional cap/face/corner or ordinary stone steps stays at native pixel size. The three south-facing exit warps519 retain their true original coordinates; the native outside threshold remains in the row below, matching the original Crystal UnionCave exit metaphor. The separate572 south-jump ledge is not mistaken for another portal.'
            self.emit_checked(group, art, reason, proof)

    def underwater_straight_faces(self):
        sides = {535:(6,3), 533:(4,2), 542:(12,3), 644:(12,3), 653:(6,3), 654:(4,2)}
        for group in self.group_list:
            binding = UNDERWATER_SIDE_BINDINGS.get(group['source_identity'])
            if binding is None:
                continue
            assert (group['family'], group['mid']) == (binding['family'], binding['mid'])
            assert {s['game'] + '/' + s['pair']: s['hash'] for s in group['source']} == binding['source_sha256'], 'Reviewed underwater source RGBA changed'
            mid = group['mid']
            if mid == 681:
                assert all(s['behavior_hint'] == 'MB_NO_SURFACING' for s in group['source'])
                assert all(c[2] == 41 for s in group['source'] for context in s['contexts'] for c in context['coordinates']), 'Reviewed deep pocket is not native water'
                ref = self.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
                program = specification(self.cache, ref, 'program')
                assert program
                art = self.native(ref, 'reverse_gen2_hoenn_underwater_no_surface_water')
                art.update(animated=True, animation=program, animationCategory='water', overMask='0' * 256)
                reason = 'Actual UnderwaterRoute127 joins identify this complete open-water pocket inside the raised reef. Its explicit MB_NO_SURFACING behavior and original Surf collision41 remain intact. It uses the same complete original Crystal CAVE20 water glyph, palette and cached native animation as the adjoining selected-style water family, never a flat recolored floor or a removed no-surface restriction.'
            else:
                bid, q = sides[mid]
                ref = self.underwater_ref(bid, q)
                art = self.native(ref, 'reverse_gen2_hoenn_underwater_straight_face_' + str(mid))
                art['overMask'] = '0' * 256
                reason = 'Full original UnderwaterRoute127 source grids distinguish flat raised reef531 and walkable seafloor534 from these straight cliff faces.535/653 face east,533/654 face west and542/644 are south-facing front bands. Their complete original Crystal stone faces stay at1:1 in the reviewed original Cianwood DAY blue palette, matching the existing coherent reef material without flattening a bank into floor or rotating its highlights. No boat, inscription, doorway or corner is inferred from a purple thumbnail.'
            self.emit_checked(group, art, reason, dict(native_ref=ref, source_context='underwater-127-contexts.json',
                                                     source_mid=mid, native_dimensions=[16,16],
                                                     native_palette_source=['crystal','CIANWOOD_CITY','DAY',20,4] if mid != 681 else ['crystal','UNION_CAVE_1F','DAY'],
                                                     preserved_source_no_surfacing=mid == 681))

    def sootopolis_limestone_walls(self):
        # Joined original source establishes the handed joins:723 runs into
        # front737 on its RIGHT and east face730 BELOW;724 is the converse,
        # with front737 LEFT and west face728 BELOW. These are INNER joins,
        # not the superficially similar outward north caps.
        refs = {723:(16,3), 724:(17,2), 728:(4,2), 730:(6,3),
                736:(12,2), 737:(12,3), 738:(14,3)}
        palette = self.limestone_floor()[0]['donor']['palettes']
        for group in self.group_list:
            binding = LIMESTONE_WALL_BINDINGS.get(group['source_identity'])
            if binding is None:
                continue
            assert (group['family'], group['mid']) == (binding['family'], binding['mid'])
            assert {s['game'] + '/' + s['pair']: s['hash'] for s in group['source']} == binding['source_sha256'], 'Reviewed limestone wall source changed'
            mid = group['mid']
            bid, q = refs[mid]
            ref = self.gb_ref('crystal', 'UNION_CAVE_1F', bid, q)
            ref['palettes'] = copy.deepcopy(palette)
            art = self.native(ref, 'reverse_gen2_hoenn_sootopolis_limestone_wall_' + str(mid))
            art['overMask'] = '0' * 256
            self.emit_checked(group, art,
                              'The complete original Sootopolis joined cliff system establishes728 as the west face,730 as east,736 as convex southwest,737 as the south-facing front mass and738 as convex southeast.723 joins front737 to its right with east face730 below, and724 joins front737 left with west face728 below; these are the corresponding original Crystal INNER wall joins16q3/17q2, not outward north corners. Whole original cave stone glyphs keep their direction, highlights and original pixel size in the same actual Crystal gray-stone palette as limestone floor729. Original terraces, collision, elevations, stairs, source events and buildings stay unchanged.',
                              dict(native_ref=ref, native_dimensions=[16,16], source_mid=mid,
                                   native_palette_source=['crystal','SAFFRON_CITY','DAY',0],
                                   source_joined_map='EM_SOOTOPOLIS_CITY',
                                   source_neighbor_contract={'723':{'east':737,'south':730},'724':{'west':737,'south':728},
                                                             '736':{'north':728,'east':737},'738':{'north':730,'west':737}},
                                   matched_floor_source=729, inner_join=mid in (723,724)))

    def volcanic_core(self):
        # The joined original MtChimney/FieryPath grids show the same rock
        # material already selected for625.624/774 are west faces,626 east,
        #628 south front,632/634 lower convex caps.638/639 are the complete
        #end caps of those respective side ridges within solid rock625.
        shapes = {624:'w', 626:'e', 628:'front', 632:'sw', 634:'se',
                  638:'sw', 639:'se', 774:'w'}
        for group in self.group_list:
            binding = VOLCANIC_CORE_BINDINGS.get(group['source_identity'])
            if binding is None:
                continue
            assert (group['family'], group['mid']) == (binding['family'], binding['mid'])
            assert {s['game'] + '/' + s['pair']: s['hash'] for s in group['source']} == binding['source_sha256'], 'Reviewed volcanic source changed'
            mid = group['mid']
            if mid in (776,930):
                ref = self.gb_ref('crystal', 'UNION_CAVE_1F', 2, 0)
                art = self.native(ref, 'reverse_gen2_hoenn_volcanic_cave_walk_floor')
                art['overMask'] = '0' * 256
                proof = dict(native_ref=ref, source_feature='ordinary native cave walk floor')
                reason = 'Original FieryPath776 and MagmaHideout930 are actual ordinary walkable cave floor, not the solid volcanic backing625 or a cliff face. The complete original Crystal cave floor remains at1:1 while every ash/lava/warp/encounter flag and source map state stays unchanged.'
            else:
                shape = shapes[mid]
                background = 'front' if shape == 'front' else 'top'
                art = self.classic_cliff(shape, background)
                art['role'] = 'reverse_gen2_hoenn_volcanic_cliff_' + str(mid)
                proof = dict(native_complete_outcrop=['crystal','VIOLET_CITY',10], shape=shape,
                             background=background, matching_existing_solid_rock_source=625,
                             source_context=['chimney-contexts.json','fiery-path-contexts.json'])
                reason = 'Complete original MtChimney and FieryPath joined grids establish this solid volcanic west/east/front face, convex lower cap or side-ridge end. The same complete original Crystal Violet outcrop8px modules and raised-stone backing as the already selected625 join at native pixel size. Whole ordinary rock fill replaces only the donor exterior field, so a green grass patch is never baked into these solid rock cells. The original native cliff direction, walk floor, lava boundary, heights and event data remain intact; no corner or wall is flattened into general ground.'
            self.emit_checked(group, art, reason, proof)

    def coast_rocks(self):
        # Route130373/374 above381/382 is one WHOLE32px rock island;
        # Route126827/829 are its upper caps in a taller island bank.
        # The same32px original Violet outcrop supplies all four caps,
        # rather than centering a smaller rock in a still-blocked footprint.
        shapes = {370:'nw',373:'nw',374:'ne',380:'e',381:'sw',382:'se',388:'se',
                  827:'nw',828:'top',829:'ne',837:'se'}
        water = self.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
        program = specification(self.cache, water, 'program')
        assert program
        for group in self.group_list:
            binding = COAST_ROCK_BINDINGS.get(group['source_identity'])
            if binding is None:
                continue
            assert (group['family'], group['mid']) == (binding['family'], binding['mid'])
            assert {s['game'] + '/' + s['pair']: s['hash'] for s in group['source']} == binding['source_sha256'], 'Reviewed whole coast source changed'
            mid = group['mid']
            shape = shapes[mid]
            art = self.classic_cliff(shape)
            art.pop('base', None)
            art['parts'] = [dict(donor=water, srcX=0, srcY=0, w=16, h=16, x=0, y=0, animated=True)] + art['parts']
            assert len(art['parts']) <= 32
            art.update(role='reverse_gen2_hoenn_coast_whole_rock_' + str(mid), animated=True,
                       animation=program, animationCategory='water', overMask='0' * 256)
            self.emit_checked(group, art,
                              'Actual complete Route130/126 source grids show the full373/374+381/382 two-by-two rock island and the same raised ocean-bank caps/side faces. All four complete original Crystal Violet32px outcrop quadrants retain their original pixel size and join the matching existing378west/386southwest banks and379raised top. A smaller centered boulder is not substituted for this full32px blocking rock. Only original exterior field becomes the same canonical animated Crystal CAVE20 water; the rock caps, west/east shading, lower faces, complete island silhouette and source Surf/collision boundaries remain distinct. Mossdeep827/829 are the paired upper rock caps,828the solid top and837the lower-right foot of the connected taller rim, not plain water.',
                              dict(native_complete_rock=['crystal','VIOLET_CITY',10], native_dimensions=[32,32],
                                   native_water=water, native_shape=shape, source_mid=mid,
                                   whole_source_rock=[[373,374],[381,382]],
                                   source_context=['coast-130-contexts.json','coast-126-contexts.json'],
                                   original_pixel_scale=1, source_blocking_footprint_preserved=True))

    def correct_coast_southeast_caps(self):
        water = self.gb_ref('crystal', 'UNION_CAVE_1F', 15, 0)
        program = specification(self.cache, water, 'program')
        art = self.classic_cliff('se')
        art.pop('base', None)
        art['parts'] = [dict(donor=water, srcX=0, srcY=0, w=16, h=16, x=0, y=0, animated=True)] + art['parts']
        art.update(role='reverse_gen2_hoenn_corrected_coast_southeast_cap', animated=True,
                   animation=program, animationCategory='water', overMask='0' * 256)
        changed=[]
        templates = {identity(row): row for row in self.templates}
        for label, binding in COAST_SE_FIX_BINDINGS.items():
            game, pair, value = label.split('/')
            mid = int(value)
            key = game, 'gen2', pair, mid, None
            if key not in self.locations:
                # Integration removes only these exact superseded literals.
                # A later author run reconstructs the shipped own-module row
                # without pretending its already-removed predecessor exists.
                template = templates[key]
                assert template['sourceHash'] == self.imp.cell_index(game)[pair,mid]['pixel_sha256']
                assert all(template.get(field) == value for field,value in art.items()), 'Previously reviewed cap artwork changed; re-review before regenerating'
                assert template['compositionPixelHash'] == catalog.sha(self.render(template).tobytes())
                self.rows[key] = copy.deepcopy(template)
                changed.append(dict(game=game,pair=pair,mid=mid,already_integrated_template=True,
                                    affected_logical_cells=self.counts[game,pair,mid]))
                continue
            module, index, old = self.locations[key]
            assert module == binding['module'] and digest(old) == binding['full_old_row_sha256']
            assert old['sourceHash'] == binding['source_hash']
            source = self.imp.cell_index(game)[pair, mid]
            geometry = [catalog.sha(part) for part in native_geometry(self, game, pair, mid)]
            source_identity = digest(['primary', mid, source['behavior'], geometry])
            proof = dict(native_complete_rock=['crystal','VIOLET_CITY',10], native_shape='se',
                         source_mid=mid, source_context=['coast-130-contexts.json','coast-126-contexts.json'],
                         source_whole_rock=[[373,374],[381,382]],
                         correction='A full frontal rock face is replaced by the actual southeast outer cap and its exterior animated water',
                         existing_west_and_southwest_rows_unchanged=[378,381,386], native_dimensions=[32,32])
            new = self.replace_art(old, art,
                                   'Independent joined Route130/126 source review proves382 is the southeast quadrant of the complete373/374+381/382 rock and388 is the same convex southeast foot of the larger ocean rim. The former full-front mass incorrectly filled its actual exterior corner with stone. The complete original Crystal southeast outcrop cap now joins the already correct native west/southwest pieces, exposing canonical animated water only outside the true rock silhouette. Native source blockers, Surf boundaries, elevations, events and all other mapped art remain unchanged.', proof)
            new['reverseGen2HoennOutdoorComplete'] = dict(source_family='primary', source_mid=mid,
                                                        source_geometry_behavior_identity=source_identity,
                                                        source_geometry_sha256=geometry, proof=proof, pixel_scale=1,
                                                        supersedes_exact_full_old_row_sha256=digest(old))
            changed.append(dict(game=game, pair=pair, mid=mid, old_module=module,
                                old_row_sha256=digest(old), affected_logical_cells=self.counts[game,pair,mid]))
        self.proofs['corrected_existing_coast_southeast_caps'] = changed

    def petalburg_joins(self):
        field = ground_ref(self, 'gen2')
        pair = 'general__petalburg'
        roots = {q: self.park_tree_art(q, field) for q in (0, 1, 2, 3)}
        roof = Image.new('RGBA', (64, 64))
        roof_pieces = {}
        for y in range(4):
            for x in range(4):
                art = native_piece(self, 'gen2', 'mart', x, y)
                roof_pieces[x, y] = art
                roof.paste(self.render(art), (x * 16, y * 16))
        outside = exterior(roof, set(self.gb_image(field).get_flattened_data()) | {(222, 255, 222, 255)})
        models = {}
        for x in range(4):
            mask = [(x * 16 + xx, yy) not in outside for yy in range(16) for xx in range(16)]
            models[x] = mask_piece(self, roof_pieces[x, 0], mask, field, True)
        for group in self.group_list:
            binding = PETALBURG_BINDINGS.get(group['source_identity'])
            if binding is None:
                continue
            assert (group['family'], group['mid']) == (binding['family'], binding['mid'])
            assert {s['game'] + '/' + s['pair']: s['hash'] for s in group['source']} == binding['source_sha256'], 'Petalburg reviewed source RGBA changed'
            mid = group['mid']
            proof = dict(source_context='petalburg-contexts.json', source_mid=mid,
                         complete_native_park_tree=[6, 48, 2, 2], original_source_size=True)
            if group['family'] == 'primary':
                if mid in (508, 509):
                    art = copy.deepcopy(roots[mid - 508])
                    reason = 'The source is the complete upper half of a two-cell-wide tree at the shore, above the already selected lower native Park tree halves. The entire original Crystal32px canopy joins those existing roots at1:1. The extra original walkable water-row apex remains water because this complete native tree already fits the lower32px envelope.'
                elif mid == 304:
                    art = self.native(field, 'reverse_gen2_hoenn_gym_sign_clear_upper_field')
                    art['overMask'] = '0' * 256
                    reason = 'The actual source304/305 is one readable outdoor GYM sign, not a curb. The complete original Crystal16px freestanding sign is anchored in the original lower blocked cell305; its extra walkable upper source cell304 exposes the matching field. This native-size counterpart needs no shortened text/frame, scaling or invisible blocker, and the original gym sign text event stays intact.'
                else:
                    art = self.active_art('emerald', pair, 3)
                    reason = 'The actual source304/305 is one readable outdoor GYM sign. Its functional classic counterpart is the complete original Crystal freestanding information sign, anchored in the same lower blocked cell. The original gym text event, access and collision stay unchanged; the extra upper source cell is walkable matching field.'
            elif mid in (594, 595):
                art = self.active_art('emerald', pair, 297)
                reason = 'This source is the existing south sand/path-to-field transition plus a tiny decorative next-tree apex. The complete native32px Park tree below already includes its own whole canopy, so the exact already selected native sand/field edge is retained without a third-row fragment or extra obstacle.'
            elif mid in (592, 593):
                x = mid - 592
                art = copy.deepcopy(models[x])
                reason = 'This source contains the upper Mart roof cap and a cosmetic shore lip on walkable exterior ground. It receives the same complete original Crystal Mart upper roof row as the existing unchanged64px-wide roof/facade below, at its original pixel size. True roof-corner exterior exposes matching native field, and only real roof pixels retain foreground priority.'
            elif mid in (600, 601):
                x = mid - 598
                root = roots[x]
                art = copy.deepcopy(models[x])
                art['parts'] = copy.deepcopy(root['parts']) + art['parts']
                assert len(art['parts']) <= 32
                reason = 'The source combines the lower native tree quarter with the complete Mart roof above the same existing clinic/shop body. The original Crystal Park roots remain behind the full original Mart roof; only opaque roof pixels obscure them. Both full objects retain native pixel size, source entrance alignment and the original roof foreground mask.'
                proof.update(native_tree_quadrant=x, tree_behind_roof=True)
            else:
                q = {589: 2, 590: 3, 597: 2, 598: 3}[mid]
                hedge_mid = {589: 588, 590: 588, 597: 580, 598: 582}[mid]
                mask = [y >= 8 or (mid == 597 and x < 8) or (mid == 598 and x >= 8)
                        for y in range(16) for x in range(16)]
                hedge = self.active_art('emerald', pair, hedge_mid)
                art = copy.deepcopy(roots[q])
                art['parts'] += self.clipped_parts(hedge, mask)
                assert len(art['parts']) <= 32
                art['overMask'] = '0' * 256
                reason = 'The actual joined source places a low leafy hedge in front of the lower tree quarter. Its whole original Crystal Park tree quarter remains behind the same already selected native low-hedge leaf modules, with complete8px modules at the same bottom/side junction. This is genuine hedge occlusion, not a cut-off canopy, resized tree or unrelated fence.'
                proof.update(native_tree_quadrant=q, native_hedge_source=hedge_mid, hedge_occludes_lower_tree=True)
            art['role'] = 'reverse_gen2_hoenn_petalburg_complete_join_' + str(mid)
            self.emit_checked(group, art, reason, proof)
        roof.save(self.out / 'complete-native-petalburg-mart64.png')

    def source_map(self, game, name):
        key = game, name
        if key not in self._source_maps:
            layout = self.native_layout(game, name)
            image = self.imp.gba(game, name)[0]
            self._source_maps[key] = image.crop((0, 0, layout['width'] * 16, layout['height'] * 16))
        return self._source_maps[key]

    def themed_map(self, game, name, include_new=True):
        layout = self.native_layout(game, name)
        image = self.source_map(game, name).copy()
        selected = {r['id']: r for r in self.prior if r['game'] == game and r['style'] == 'gen2'
                    and r['tileset'] == layout['pair'] and r.get('map') is None}
        if include_new:
            selected.update({r['id']: r for r in self.rows.values() if r['game'] == game and r['style'] == 'gen2'
                             and r['tileset'] == layout['pair']})
        for number, mid in enumerate(layout['mids']):
            row = selected.get(mid)
            if row is None:
                continue
            key = row['compositionPixelHash']
            if key not in self._rendered_rows:
                self._rendered_rows[key] = self.render(row)
            image.paste(self._rendered_rows[key], (number % layout['width'] * 16, number // layout['width'] * 16))
        return image

    def context_contact(self, game, name, mids, stem):
        layout = self.native_layout(game, name)
        before = self.source_map(game, name)
        current = self.themed_map(game, name, False)
        before.save(self.out / f'{stem}-original.png')
        current.save(self.out / f'{stem}-current.png')
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 12)
        records = []
        for mid in mids:
            positions = [(i % layout['width'], i // layout['width']) for i, value in enumerate(layout['mids']) if value == mid]
            if not positions:
                continue
            x, y = positions[0]
            left, top = max(0, x - 2), max(0, y - 2)
            right, bottom = min(layout['width'], x + 3), min(layout['height'], y + 3)
            records.append(dict(mid=mid, positions=positions, marked=[x, y], bounds=[left, top, right, bottom],
                                source_cells=[[layout['cells'][yy * layout['width'] + xx] for xx in range(left, right)] for yy in range(top, bottom)]))
        for start in range(0, len(records), 12):
            panel = Image.new('RGB', (4 * 396, 3 * 286), '#18212b')
            draw = ImageDraw.Draw(panel)
            for number, record in enumerate(records[start:start + 12]):
                dx, dy = number % 4 * 396, number // 4 * 286
                left, top, right, bottom = record['bounds']
                rect = left * 16, top * 16, right * 16, bottom * 16
                for col, image in enumerate((before, current)):
                    cropped = image.crop(rect)
                    panel.paste(cropped.resize((cropped.width * 2, cropped.height * 2), Image.Resampling.NEAREST), (dx + 4 + col * 192, dy + 28))
                    x, y = record['marked']
                    draw.rectangle((dx + 4 + col * 192 + (x - left) * 32, dy + 28 + (y - top) * 32,
                                    dx + 35 + col * 192 + (x - left) * 32, dy + 59 + (y - top) * 32), outline='#ffdd66', width=1)
                draw.text((dx + 4, dy + 4), f"{game} / {name[3:]} MID {record['mid']}", fill='white', font=font)
                draw.text((dx + 4, dy + 196), '\n'.join(' '.join(f'{c[0]:3}:{c[1]:02x}/{c[2]:x}' for c in row) for row in record['source_cells']), fill='#b8cfde', font=font)
            panel.save(self.out / f'{stem}-contexts-{start // 12 + 1:02}.png')
        (self.out / f'{stem}-contexts.json').write_text(json.dumps(dict(game=game, map=name, pair=layout['pair'], records=records), indent=2) + '\n')
        return records

    def build(self):
        self.petalburg_joins()
        self.rusturf_core()
        self.underwater_straight_faces()
        self.sootopolis_limestone_walls()
        self.volcanic_core()
        self.coast_rocks()
        self.correct_coast_southeast_caps()
        (self.out / 'supersessions.json').write_text(json.dumps(list(self.supersessions.values()), indent=2) + '\n')
        (self.out / 'pixel-preservation-proofs.json').write_text(json.dumps(self.proofs, indent=2) + '\n')
        report = dict(rows=len(self.rows), reviewed_groups=len(self.recipes),
                      new_logical_cells=sum(s['occurrences'] for g in self.group_list if g['source_identity'] in self.recipes for s in g['missing']),
                      superseded_rows=len(self.supersessions),
                      corrected_existing_logical_cells=sum(self.counts[k[0],k[2],k[3]] for k in self.supersessions))
        (self.out / 'coverage-stage.json').write_text(json.dumps(report, indent=2) + '\n')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', action='store_true')
    parser.add_argument('--no-contacts', action='store_true')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    review = Review()
    report = review.inventory(not args.no_contacts)
    if args.build or args.validate:
        report['stage'] = review.build()
        review.write(review.out / 'candidates.lua')
        if args.validate:
            report['validation'] = review.validate()
    (review.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
