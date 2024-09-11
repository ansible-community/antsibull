Hello everyone,

We're happy to announce the release of the Ansible 7.4.0 package!

Ansible 7.4.0 depends on ansible-core 2.14.4 and includes a curated set of Ansible collections that provide a vast number of modules, plugins, and roles.

How to get it
-------------

This release is available on PyPI and can be installed with pip:

```console
python3 -m pip install ansible==7.4.0 --user
```

The sources for this release can be found here:

Release tarball:

https://files.pythonhosted.org/packages/45/4b/2087a0fe8265828df067e57d7d156426cdc8f7cd94ad3178c6510d81e2c0/ansible-7.4.0.tar.gz

SHA256:

0964d6ec7b363d2d559f245c39b01798c720a85b207672ec2c9d83cf61564b90

Wheel package:

https://files.pythonhosted.org/packages/0d/34/1b50f134f3136eeddf87f1b50253c1dece059407f5de57044963c82d07c0/ansible-7.4.0-py3-none-any.whl

SHA256:

c9b5cae2ff8168b3dc859fff12275338cd7c84ef37f62889076f82846bb4beb5


Some important details
----------------------

ansible-core is a separate package on which ansible depends. `pip install ansible` installs `ansible-core`, but it can also be installed independently of the ansible package.

Collections that have opted to join the Ansible 7 unified changelog will have an entry on this page:

https://github.com/ansible-community/ansible-build-data/blob/7.4.0/7/CHANGELOG-v7.md

For collections which have not opted-in to the unified changelog, you may find more information on

https://docs.ansible.com/ansible/latest/collections

or on the collection source repository. For example, the community.crypto collection is available at

https://docs.ansible.com/ansible/latest/collections/community/crypto/index.html

and you can find a link to the source repository under the “Repository (Sources)” button.

The changelog for ansible-core 2.14 installed by this release of Ansible 7 can be found here:

https://github.com/ansible/ansible/blob/v2.14.4/changelogs/CHANGELOG-v2.14.rst

What's the schedule for new Ansible releases after 7.4.0?
---------------------------------------------------------

The next release roadmap can be found at

https://docs.ansible.com/ansible/devel/roadmap/ansible_roadmap_index.html

The Ansible community package release schedule follows the Ansible Core release schedule, including, for example, delays for holidays. This means Ansible releases happen every four weeks through most of the year, but release dates may be delayed when Ansible Core releases are.

Subscribe to the Bullhorn for all future release dates, announcements, and Ansible contributor community news.

Visit this link to subscribe: https://bit.ly/subscribe-bullhorn

You can find all past Bullhorn issues on the Ansible Community Forum at:

https://forum.ansible.com/c/news/bullhorn/17

Join the new Ansible Community Forum to follow along and participate in all the project and release related discussions and announcements. Feel free to share your thoughts, feedback, ideas and concerns there.

Register here to join the Ansible Forum:

https://forum.ansible.com

Porting Help
------------

A unified porting guide for collections that have opted in is available here:

https://docs.ansible.com/ansible/devel/porting_guides/porting_guide_7.html

Getting collection updates from Ansible 7 with older releases of ansible-core
-----------------------------------------------------------------------------

Ansible 7 depends on ansible-core 2.14. Depending on your needs, you can get collection updates as they ship in the Ansible “batteries included” package while continuing to use older versions of ansible-core.

See the ansible-galaxy requirements file based on the collections from Ansible 7 for this use case:

https://github.com/ansible-community/ansible-build-data/blob/7.4.0/7/galaxy-requirements.yaml

After you download the requirements file, you can install the collections by running the following command:

```console
ansible-galaxy collection install -r galaxy-requirements.yaml
```

On behalf of the Ansible community, thank you and happy automating!

Cheers,
Ansible Release Management Working Group
