from setuptools import setup

package_name = 'awsiotcore_to_navigation2'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Tokuro Kono',
    maintainer_email='tokuro_kono@r.recruit.co.jp',
    description='Receive positional information '
                'from AWS IoT Core and send it to Navigation2',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'iotcore_to_nav2 = '
            'awsiotcore_to_navigation2.awsiotcore_to_nav2_node:main'
        ],
    },
)
