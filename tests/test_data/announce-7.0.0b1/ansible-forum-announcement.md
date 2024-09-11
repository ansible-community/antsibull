Hello everyone,

We're happy to announce the release of the Ansible 7.0.0b1 package pre-release!

Ansible 7.0.0b1 depends on ansible-core 2.14.0 and includes a curated set of Ansible collections that provide a vast number of modules, plugins, and roles. This is a pre-release of Ansible 7.

How to get it
-------------

This pre-release is available on PyPI and can be installed with pip:

```console
python3 -m pip install ansible==7.0.0b1 --user
```

The sources for this release can be found here:

Release tarball:

https://files.pythonhosted.org/packages/0b/b3/198b439cd7360c74bd91767e995e588ab0c4a65c17cd7bba340c3b0995b1/ansible-7.0.0b1.tar.gz

SHA256:

f665e35f381f4e1cd600e2ad70d7a7bb3949340114030940460fc4e249f9b0e7

Wheel package:

https://files.pythonhosted.org/packages/bc/85/ade95555a7602c3a8d813d718ece7e91d61599f31d72ceda9c12b19a43a8/ansible-7.0.0b1-py3-none-any.whl

SHA256:

11f812a1c46a7ab4e298ceed25cc2c47d0ed23b6b972a9f6f3e2661b6d762f85


Some important details
----------------------

ansible-core is a separate package on which ansible depends. `pip install ansible` installs `ansible-core`, but it can also be installed independently of the ansible package.

Collections that have opted to join the Ansible 7 unified changelog will have an entry on this page:

https://github.com/ansible-community/ansible-build-data/blob/7.0.0b1/7/CHANGELOG-v7.md

For collections which have not opted-in to the unified changelog, you may find more information on

https://docs.ansible.com/ansible/latest/collections

or on the collection source repository. For example, the community.crypto collection is available at

https://docs.ansible.com/ansible/latest/collections/community/crypto/index.html

and you can find a link to the source repository under the “Repository (Sources)” button.

The changelog for ansible-core 2.14 installed by this release of Ansible 7 can be found here:

https://github.com/ansible/ansible/blob/v2.14.0/changelogs/CHANGELOG-v2.14.rst

What's the schedule for new Ansible releases after 7.0.0b1?
-----------------------------------------------------------

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

https://github.com/ansible-community/ansible-build-data/blob/7.0.0b1/7/galaxy-requirements.yaml

After you download the requirements file, you can install the collections by running the following command:

```console
ansible-galaxy collection install -r galaxy-requirements.yaml
```

On behalf of the Ansible community, thank you and happy automating!

Cheers,
Ansible Release Management Working Group
